"""Independent estates and shared YAML composition, with no live credentials or cookbook imports."""

import asyncio
import json
from datetime import UTC, datetime

import httpx
import networkx as nx
import pytest
from typer.testing import CliRunner

from lumis_sdk.cli.app import app
from lumis_sdk.connectors.kubernetes import topology_from_kubernetes
from lumis_sdk.connectors.service_graph import topology_from_service_graph
from lumis_sdk.core import Entity, GraphSnapshot, Incident, Relationship
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.graph.identity import link_kubernetes_services, normalize_identities
from lumis_sdk.runtime import DiscoveryError, DiscoveryReport, YamlProject
from lumis_sdk.runtime.project import OperationalProject
from lumis_sdk.runtime.scaffold import starter_documents


def write_project(tmp_path, config=None):
    for name, content in starter_documents().items():
        (tmp_path / name).write_text(content)
    path = tmp_path / "lumis.yaml"
    if config is not None:
        path.write_text(json.dumps(config))
    return path


def graph_fixture():
    return GraphSnapshot(
        entities=tuple(
            Entity(
                id=key,
                kind="job" if key == "job" else "dataset",
                name=key,
                attributes={"owner": "data"},
            )
            for key in ("raw", "job", "features")
        ),
        relationships=(
            Relationship(source="raw", target="job", kind="feeds"),
            Relationship(source="raw", target="job", kind="observed_dependency"),
            Relationship(source="job", target="features", kind="produces"),
        ),
    )


def vector(value="1", *, client="frontend", server="database"):
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [{"metric": {"client": client, "server": server}, "value": [123, value]}],
        },
    }


def test_networkx_preserves_multiedges_direction_and_safe_exports():
    original = graph_fixture()
    graph = OperationalGraph(original)
    original.entities[0].attributes["owner"] = "mutated"
    exported = graph.to_networkx()
    assert isinstance(exported, nx.MultiDiGraph)
    assert exported.number_of_edges("raw", "job") == 2
    exported.nodes["raw"]["attributes"]["owner"] = "caller"
    exported.remove_node("job")
    assert graph.snapshot().entities[0].attributes["owner"] == "data"
    scoped = graph.dependencies_within("features", hops=1)
    assert {item.id for item in scoped.entities} == {"job", "features"}
    assert graph.upstream_of("features") == ("job", "raw")
    assert graph.downstream_of("raw") == ("features", "job")
    graph.snapshot().entities[0].attributes["owner"] = "another caller"
    assert graph.snapshot().entities[0].attributes["owner"] == "data"
    assert '"raw" -> "job" [label="feeds"]' in graph.to_dot()
    assert len(graph.scope(("raw",), hops=0).entities) == 1
    for kwargs in ({"hops": -1}, {"max_entities": 1}, {"max_entities": 0}):
        with pytest.raises(ValueError):
            graph.dependencies_within("features", **kwargs)
    with pytest.raises(ValueError, match="unknown"):
        graph.dependencies_within("missing")


def test_cycle_bounds_and_invalid_snapshot_revalidation():
    snapshot = graph_fixture()
    snapshot = GraphSnapshot(
        entities=snapshot.entities,
        relationships=(
            *snapshot.relationships,
            Relationship(source="features", target="raw", kind="loop"),
        ),
    )
    assert len(OperationalGraph(snapshot).scope(("raw",), hops=500).entities) == 3
    with pytest.raises(ValueError):
        OperationalGraph(snapshot.model_copy(update={"entities": ()}))


def test_resource_service_bridge_joins_telemetry_without_collapsing_resource():
    kube = topology_from_kubernetes(
        {
            "items": [
                {
                    "kind": "Pod",
                    "metadata": {
                        "name": "frontend-1",
                        "namespace": "web",
                        "labels": {"app.kubernetes.io/name": "frontend"},
                    },
                }
            ]
        },
        namespace="web",
    )
    linked = link_kubernetes_services(kube)
    graph = OperationalGraph(linked)
    assert graph.upstream_of("service:web:frontend") == ("k8s:web:pod:frontend-1",)
    assert len(linked.entities) == 2
    assert linked.relationships[0].kind == "hosts"


def test_aliases_explicit_only_preserve_kinds_and_reject_conflicts():
    raw = GraphSnapshot(entities=(Entity(id="service:old", kind="service", name="Old"),))
    declared = GraphSnapshot(
        entities=(Entity(id="service:canonical", kind="service", name="Canonical"),)
    )
    normalized = normalize_identities(raw, {"service:old": "service:canonical"}, declared)
    assert normalized.entities[0].name == "Canonical"
    assert normalize_identities(raw, {}, declared).entities[0].id == "service:old"
    with pytest.raises(ValueError, match="incompatible"):
        normalize_identities(graph_fixture(), {"raw": "service:canonical"}, declared)
    base = {"project": {"name": "test"}}
    for aliases in ({"a": "a"}, {"a": "b", "b": "c"}, {"a": "b", "b": "a"}):
        with pytest.raises(ValueError, match="alias"):
            OperationalProject.model_validate(base | {"identity": {"aliases": aliases}})


@pytest.mark.parametrize(
    "patch",
    [
        {"enabled": "false"},
        {"enabled": True, "endpoint": "http://example.test", "discover_service_graph": True},
        {"enabled": False, "discover_service_graph": True, "service_namespace": "web"},
    ],
)
def test_service_graph_configuration_is_explicit(patch):
    with pytest.raises(ValueError):
        OperationalProject.model_validate(
            {"project": {"name": "test"}, "sources": {"prometheus": patch}}
        )


@pytest.mark.parametrize("value", ["NaN", "Inf", "-1", True])
def test_service_graph_refuses_nonfinite_negative_and_boolean_samples(value):
    with pytest.raises(ValueError):
        topology_from_service_graph(vector(value), namespace="web")


def test_service_graph_direction_empty_and_partial_data():
    graph = topology_from_service_graph(vector(), namespace="web")
    assert graph.relationships[0].source == "service:web:database"
    assert graph.relationships[0].target == "service:web:frontend"
    assert not topology_from_service_graph(vector("0"), namespace="web").entities
    with pytest.raises(ValueError):
        topology_from_service_graph(vector() | {"warnings": ["partial"]}, namespace="web")
    with pytest.raises(ValueError):
        topology_from_service_graph(vector(), namespace="")
    payload = vector()
    payload["data"]["result"] *= 2
    with pytest.raises(ValueError, match="budget"):
        topology_from_service_graph(payload, namespace="web", max_series=1)


def test_two_line_api_offline_and_prepared_reuse(tmp_path):
    config = json.loads(starter_documents()["lumis.yaml"])
    config["observations_file"] = "observations.json"
    path = write_project(tmp_path, config)
    incident = Incident.model_validate_json((tmp_path / "incident.json").read_text())

    async def run():
        project = YamlProject.from_file(path)
        result = await project.investigate(incident)
        prepared = await project.prepare()
        assert prepared.discovery.complete
        assert await prepared.investigate(incident) == result
        assert (await prepared.investigate(incident, observations=())).outcome == "abstained"
        assert not project.config.models
        return result

    assert asyncio.run(run()).outcome == "supported"


def test_external_topology_defers_then_strictly_binds_query_ids(tmp_path):
    config = json.loads(starter_documents()["lumis.yaml"])
    snapshot = config.pop("graph")
    config["sources"] = {"topology": {"enabled": True, "file_path": "estate.json"}}
    path = write_project(tmp_path, config)
    (tmp_path / "estate.json").write_text(json.dumps(snapshot))
    prepared = asyncio.run(YamlProject.from_file(path).prepare())
    assert prepared.graph.snapshot().entities[0].id == "service:demo"
    (tmp_path / "estate.json").write_text("{}")
    with pytest.raises(ValueError, match="prepared graph"):
        asyncio.run(YamlProject.from_file(path).prepare())


def test_yaml_prometheus_discovery_and_evidence_share_injected_client(tmp_path):
    config = json.loads(starter_documents()["lumis.yaml"])
    config.pop("graph")
    config["sources"] = {
        "prometheus": {
            "enabled": True,
            "endpoint": "http://telemetry.test",
            "discover_service_graph": True,
            "service_namespace": "web",
        }
    }
    config["identity"] = {"aliases": {"service:web:frontend": "service:demo"}}
    config["queries"][0].update({"provider": "prometheus", "parameters": {"promql": "min(up)"}})
    for check in config["rule_hypotheses"][0]["predictions"]:
        check["value"] = 0
    for check in config["rule_hypotheses"][0]["falsifiers"]:
        check["value"] = 1
    path = write_project(tmp_path, config)
    incident = Incident.model_validate_json((tmp_path / "incident.json").read_text())
    seen = []

    def handle(request):
        assert float(request.url.params["time"]) == incident.ended_at.timestamp()
        seen.append(request.url.params["query"])
        if "traces_service_graph" in seen[-1]:
            return httpx.Response(200, json=vector())
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {"resultType": "scalar", "result": [incident.ended_at.timestamp(), "0"]},
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            prepared = await YamlProject.from_file(path).prepare(
                client=client, at=incident.ended_at
            )
            assert prepared.graph.upstream_of("service:demo") == ("service:web:database",)
            result = await prepared.investigate(incident, client=client)
            assert not client.is_closed
            assert result.outcome == "supported"
        assert client.is_closed

    asyncio.run(run())
    assert len(seen) == 2


def test_discovery_failure_report_and_cli_are_fail_closed_and_sanitized(tmp_path):
    config = {
        "project": {"name": "test"},
        "sources": {
            "topology": {"enabled": True, "file_path": "missing-private-key.json"},
            "opentelemetry": {"enabled": True, "export_file": "later.json"},
        },
    }
    path = write_project(tmp_path, config)
    with pytest.raises(DiscoveryError) as caught:
        asyncio.run(YamlProject.from_file(path).prepare())
    report = caught.value.report
    assert not report.complete
    assert DiscoveryReport.model_validate_json(report.model_dump_json()) == report
    with pytest.raises(ValueError, match="completion"):
        DiscoveryReport.model_validate(report.model_dump() | {"complete": True})
    statuses = {source.name: source.status for source in report.sources}
    assert statuses["topology"] == "error"
    assert statuses["opentelemetry"] == "not_checked"
    assert "private-key" not in report.model_dump_json()
    result = CliRunner().invoke(app, ["discover", "--project", str(path), "--report"])
    assert result.exit_code == 1
    assert json.loads(result.output)["complete"] is False
    assert "private-key" not in result.output


def test_aggregate_budget_and_deadline_and_cancellation(tmp_path, monkeypatch):
    config = {
        "project": {"name": "test"},
        "graph": graph_fixture().model_dump(),
        "discovery": {"max_entities": 2},
    }
    path = write_project(tmp_path, config)
    with pytest.raises(DiscoveryError):
        asyncio.run(YamlProject.from_file(path).prepare())
    config = {
        "project": {"name": "test"},
        "sources": {"kubernetes": {"enabled": True, "context": "test", "namespace": "web"}},
        "discovery": {"timeout_seconds": 0.001},
    }
    path.write_text(json.dumps(config))

    async def slow(self):
        await asyncio.sleep(10)

    monkeypatch.setattr("lumis_sdk.runtime.discovery.KubernetesDiscovery.discover", slow)
    with pytest.raises(DiscoveryError) as caught:
        asyncio.run(YamlProject.from_file(path).prepare())
    assert any(
        source.name == "kubernetes" and source.status == "error"
        for source in caught.value.report.sources
    )

    async def cancelled(self):
        raise asyncio.CancelledError()

    monkeypatch.setattr("lumis_sdk.runtime.discovery.KubernetesDiscovery.discover", cancelled)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(YamlProject.from_file(path).prepare())


def test_graph_cli_inspection_and_report(tmp_path):
    path = write_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "graph",
            "--project",
            str(path),
            "--entity",
            "service:demo",
            "--hops",
            "0",
            "--format",
            "dot",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "digraph lumis" in result.output
    assert (
        runner.invoke(app, ["graph", "--project", str(path), "--format", "invalid"]).exit_code != 0
    )
    assert (
        runner.invoke(app, ["graph", "--project", str(path), "--entity", "absent"]).exit_code != 0
    )
    report = runner.invoke(app, ["discover", "--project", str(path), "--report"])
    assert json.loads(report.output)["complete"]


def test_discovery_time_must_be_aware(tmp_path):
    path = write_project(tmp_path)
    with pytest.raises(ValueError, match="timezone aware"):
        asyncio.run(YamlProject.from_file(path).prepare(at=datetime(2026, 10, 3)))
    assert asyncio.run(
        YamlProject.from_file(path).prepare(at=datetime(2026, 10, 3, tzinfo=UTC))
    ).discovery.complete


def test_yaml_merges_kube_and_otlp_service_identity(tmp_path, monkeypatch):
    config = {
        "project": {"name": "web"},
        "sources": {
            "kubernetes": {"enabled": True, "context": "test", "namespace": "web"},
            "opentelemetry": {"enabled": True, "export_file": "traces.json"},
        },
    }
    path = write_project(tmp_path, config)
    kube = topology_from_kubernetes(
        {
            "items": [
                {
                    "kind": "Pod",
                    "metadata": {
                        "name": "frontend-1",
                        "namespace": "web",
                        "labels": {"app.kubernetes.io/name": "frontend"},
                    },
                }
            ]
        },
        namespace="web",
    )

    async def discover(self):
        return kube

    monkeypatch.setattr("lumis_sdk.runtime.discovery.KubernetesDiscovery.discover", discover)
    (tmp_path / "traces.json").write_text(
        json.dumps(
            {
                "resourceSpans": [
                    {
                        "resource": {
                            "attributes": [
                                {"key": "service.name", "value": {"stringValue": "frontend"}},
                                {"key": "service.namespace", "value": {"stringValue": "web"}},
                                {"key": "private", "value": {"stringValue": "must-not-export"}},
                            ]
                        },
                        "scopeSpans": [],
                    }
                ]
            }
        )
    )
    prepared = asyncio.run(YamlProject.from_file(path).prepare())
    assert len(prepared.graph.snapshot().entities) == 2
    assert prepared.graph.upstream_of("service:web:frontend") == ("k8s:web:pod:frontend-1",)
    entity = next(item for item in prepared.graph.snapshot().entities if item.kind == "service")
    assert set(entity.provenance) == {"kubernetes.app-label", "opentelemetry.resource"}
    assert "must-not-export" not in prepared.discovery.model_dump_json()


def test_alias_many_to_one_merges_provenance_and_rejects_namespace_conflict():
    declared = GraphSnapshot(entities=(Entity(id="canonical", kind="service", name="Canonical"),))
    snapshot = GraphSnapshot(
        entities=(
            Entity(
                id="a",
                kind="service",
                name="A",
                attributes={"service.namespace": "web"},
                provenance=("one",),
            ),
            Entity(
                id="b",
                kind="service",
                name="B",
                attributes={"service.namespace": "web"},
                provenance=("two",),
            ),
        ),
        relationships=(Relationship(source="a", target="b", kind="same_identity"),),
    )
    normalized = normalize_identities(snapshot, {"a": "canonical", "b": "canonical"}, declared)
    assert len(normalized.entities) == 1
    assert normalized.entities[0].provenance == ("one", "two")
    assert not normalized.relationships
    conflicting = snapshot.model_copy(
        update={
            "entities": (
                snapshot.entities[0],
                snapshot.entities[1].model_copy(
                    update={"attributes": {"service.namespace": "other"}}
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="attributes"):
        normalize_identities(conflicting, {"a": "canonical", "b": "canonical"}, declared)


def test_relationship_budget_and_collision_refuse_preparation(tmp_path):
    config = {
        "project": {"name": "test"},
        "graph": graph_fixture().model_dump(),
        "discovery": {"max_relationships": 1},
    }
    path = write_project(tmp_path, config)
    with pytest.raises(DiscoveryError):
        asyncio.run(YamlProject.from_file(path).prepare())
    config.pop("discovery")
    config["sources"] = {"topology": {"enabled": True, "file_path": "collision.json"}}
    path.write_text(json.dumps(config))
    (tmp_path / "collision.json").write_text(
        GraphSnapshot(entities=(Entity(id="raw", kind="service", name="wrong"),)).model_dump_json()
    )
    with pytest.raises(DiscoveryError):
        asyncio.run(YamlProject.from_file(path).prepare())


def test_doctor_warns_about_missing_topology_but_never_discovers(tmp_path):
    config = {
        "project": {"name": "test"},
        "sources": {"topology": {"enabled": True, "file_path": "missing.json"}},
    }
    path = write_project(tmp_path, config)
    result = CliRunner().invoke(app, ["doctor", "--project", str(path)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert not payload["network_checked"]
    assert payload["warnings"] == ["Configured topology JSON snapshot is absent."]
