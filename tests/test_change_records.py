"""Typed recent-change records: Git commits on mapped paths and Kubernetes rollouts."""

import asyncio
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from lumis_sdk.connectors.changes import (
    ChangeConnector,
    commits_from_git_log,
    rollouts_from_kubernetes,
)
from lumis_sdk.connectors.settings import ChangeQuery, ChangeSource, GitChangeSource
from lumis_sdk.core import EvidenceQuery, Incident
from lumis_sdk.investigation.contracts import InspectRequest
from lumis_sdk.investigation.process import ProcessOutput
from lumis_sdk.investigation.tools import InvestigationTools
from lumis_sdk.runtime import YamlProject
from lumis_sdk.runtime.project import OperationalProject
from lumis_sdk.runtime.scaffold import starter_documents

END = datetime(2026, 10, 3, 12, 30, tzinfo=UTC)
INCIDENT = Incident(
    id="i",
    affected_entities=("service:demo",),
    symptoms=("slow builds",),
    started_at=END - timedelta(minutes=20),
    ended_at=END,
)
GITOPS = GitChangeSource(
    id="gitops",
    root="gitops",
    paths={"deploy/feature.yaml": ("service:demo",), "deploy/shared/": ("service:other",)},
)


def git_repo(path, commits):
    path.mkdir()

    def git(*args, when=None):
        env = os.environ | {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
        if when is not None:
            env |= {"GIT_COMMITTER_DATE": when.isoformat(), "GIT_AUTHOR_DATE": when.isoformat()}
        subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, env=env)

    git("init")
    git("config", "user.email", "test@example.test")
    git("config", "user.name", "Test")
    for when, file, message in commits:
        target = path / file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{message}\n")
        git("add", ".")
        git("-c", "commit.gpgsign=false", "commit", "-m", message, when=when)


def test_git_commits_on_mapped_paths_become_entity_changes(tmp_path):
    git_repo(
        tmp_path / "gitops",
        [
            (END - timedelta(hours=3), "deploy/feature.yaml", "baseline outside the lookback"),
            (END - timedelta(minutes=8), "deploy/feature.yaml", "release 1.7.0 password=hunter2x"),
            (END - timedelta(minutes=5), "README.md", "unmapped file"),
            (END - timedelta(minutes=4), "deploy/shared/db.yaml", "raise pool size"),
            (END + timedelta(minutes=5), "deploy/feature.yaml", "after the incident"),
        ],
    )
    source = ChangeSource(enabled=True, git=(GITOPS,), lookback_seconds=1800)
    connector = ChangeConnector(
        source, base=tmp_path, aliases={"service:other": "service:canonical-other"}
    )
    history = asyncio.run(connector.history(until=END))
    assert [record.summary.split(" [")[0] for record in history][0] == "raise pool size"
    assert len(history) == 2  # outside the lookback, unmapped and future commits excluded
    assert history[0].entity_ids == ("service:canonical-other",)
    assert history[1].entity_ids == ("service:demo",) and history[1].kind == "commit"
    assert "hunter2x" not in history[1].summary and "deploy/feature.yaml" in history[1].summary
    assert history[1].id == f"git:gitops:{history[1].reference}"


def test_conventional_commit_scope_narrows_a_shared_file():
    shared = GitChangeSource(
        id="gitops",
        root=".",
        paths={"kustomization.yaml": ("service:feature", "service:planning")},
        scopes={"feature-service": ("service:feature",)},
    )
    log = (
        "\x1e" + "a" * 40 + "\x1f2026-10-03T12:20:00Z\x1fdeploy(feature-service): 1.6.0 -> 1.7.0\n"
        "kustomization.yaml\n"
        "\x1e" + "b" * 40 + "\x1f2026-10-03T12:21:00Z\x1fchore: bump all\nkustomization.yaml\n"
    )
    scoped, unscoped = commits_from_git_log(log, shared, {})
    assert scoped.entity_ids == ("service:feature",)
    assert unscoped.entity_ids == ("service:feature", "service:planning")


def test_git_log_parser_refuses_unexpected_metadata():
    with pytest.raises(ValueError):
        commits_from_git_log("\x1enot-a-sha\x1f2026-10-03T12:00:00Z\x1fs\nx", GITOPS, {})


def replicaset(name, revision, image, created, app="feature-service"):
    return {
        "kind": "ReplicaSet",
        "metadata": {
            "name": name,
            "creationTimestamp": created,
            "annotations": {"deployment.kubernetes.io/revision": str(revision)},
            "ownerReferences": [{"kind": "Deployment", "name": "feature-service"}],
        },
        "spec": {
            "template": {
                "metadata": {"labels": {"app.kubernetes.io/name": app}},
                "spec": {"containers": [{"image": image}]},
            }
        },
    }


ROLLOUTS = {
    "items": [
        replicaset("feature-service-a1", 1, "feature:1.6.0", "2026-10-03T09:00:00Z"),
        replicaset("feature-service-b2", 2, "feature:1.7.0", "2026-10-03T12:22:00Z"),
        {"kind": "ReplicaSet", "metadata": {"name": "orphan"}},
    ]
}


def test_kubernetes_rollouts_name_the_deployment_and_its_service():
    records = rollouts_from_kubernetes(ROLLOUTS, namespace="gridcast", aliases={})
    latest = max(records, key=lambda record: record.at)
    assert latest.kind == "rollout" and latest.reference == "feature-service-b2"
    assert latest.entity_ids == (
        "k8s:gridcast:deployment:feature-service",
        "service:gridcast:feature-service",
    )
    assert "revision 2" in latest.summary and "feature:1.6.0 -> feature:1.7.0" in latest.summary


def fake_runner(payload, events=None):
    async def run(args, **kwargs):
        assert args[0] == "kubectl" and args[5] == "get"
        body = payload if "replicasets" in args else (events or {"items": []})
        return ProcessOutput(0, json.dumps(body).encode())

    return run


def query(output="count", **parameters):
    return EvidenceQuery(
        id="feature-rollouts",
        provider="changes",
        entity_id="service:gridcast:feature-service",
        key="rollouts_30m",
        description="Rollouts of feature-service in the 30 minutes before incident end",
        parameters={"output": output, "lookback_seconds": "1800", **parameters},
    )


def connector(payload=ROLLOUTS, events=None, **source):
    return ChangeConnector(
        ChangeSource(enabled=True, kubernetes_rollouts=True, **source),
        base=os.getcwd(),
        kubernetes=("kind-gridcast", "gridcast"),
        runner=fake_runner(payload, events),
    )


def test_reactivated_replicaset_is_a_rollout_while_its_event_lasts():
    """GitOps revert-and-reapply re-uses the old ReplicaSet: only an event records the time."""
    reused = {
        "items": [replicaset("feature-service-b2", 4, "feature:1.7.0", "2026-10-03T09:30:00Z")]
    }
    events = {
        "items": [
            {
                "reason": "ScalingReplicaSet",
                "message": "Scaled up replica set feature-service-b2 from 0 to 1",
                "lastTimestamp": "2026-10-03T12:25:00Z",
            },
            {
                "reason": "ScalingReplicaSet",
                "message": "Scaled up replica set feature-service-b2 from 1 to 2",
                "lastTimestamp": "2026-10-03T12:26:00Z",
            },
        ]
    }
    assert asyncio.run(connector(reused).collect(query(), INCIDENT))[0].value == 0
    (fact,) = asyncio.run(
        connector(reused, events).collect(query("seconds_since_latest"), INCIDENT)
    )
    assert fact.value == 300.0


def test_change_facts_count_zero_and_time_since_latest():
    (count,) = asyncio.run(connector().collect(query(), INCIDENT))
    assert count.value == 1 and count.observed_at == END and count.quality == "observed"
    (since,) = asyncio.run(connector().collect(query("seconds_since_latest"), INCIDENT))
    assert since.value == 480.0
    quiet = {"items": ROLLOUTS["items"][:1]}
    (none,) = asyncio.run(connector(quiet).collect(query(), INCIDENT))
    assert none.value == 0  # authoritative history: no change is an observation
    assert asyncio.run(connector(quiet).collect(query("seconds_since_latest"), INCIDENT)) == ()
    commits_only = query(kind="commit")
    assert asyncio.run(connector().collect(commits_only, INCIDENT))[0].value == 0


def test_truncated_history_is_degraded():
    many = {
        "items": [
            replicaset(f"feature-service-{n}", n, f"feature:{n}", f"2026-10-03T12:{n:02d}:00Z")
            for n in range(1, 5)
        ]
    }
    (fact,) = asyncio.run(connector(many, max_records=2).collect(query(), INCIDENT))
    assert fact.value == 2 and fact.quality == "degraded"


def test_change_contracts_refuse_pathspec_magic_and_unscoped_backends():
    for path in (":(glob)**", "../outside", "/etc/passwd", "-p", "deploy//x"):
        with pytest.raises(ValueError):
            GitChangeSource(id="g", root=".", paths={path: ("service:demo",)})
    with pytest.raises(ValueError, match="requires git"):
        ChangeSource(enabled=True)
    with pytest.raises(ValueError):
        ChangeQuery(output="latest_author")
    with pytest.raises(ValueError, match="Kubernetes"):
        ChangeConnector(ChangeSource(enabled=True, kubernetes_rollouts=True), base=os.getcwd())


def project_config(tmp_path, *, sources):
    config = json.loads(starter_documents()["lumis.yaml"])
    config["sources"] = sources
    config["queries"].append(
        {
            "id": "release-changes",
            "provider": "changes",
            "entity_id": "service:demo",
            "key": "release_changes_30m",
            "description": "Commits to the service's GitOps manifest in the last 30 minutes",
            "parameters": {"lookback_seconds": "1800"},
        }
    )
    return config


def test_project_requires_enabled_backends_for_change_queries(tmp_path):
    config = project_config(tmp_path, sources={})
    with pytest.raises(ValueError, match="enabled source"):
        OperationalProject.model_validate(config)
    config["sources"] = {"changes": {"enabled": True, "kubernetes_rollouts": True}}
    with pytest.raises(ValueError, match="Kubernetes"):
        OperationalProject.model_validate(config)


def test_incident_triage_and_agent_tool_see_recent_changes(tmp_path):
    git_repo(
        tmp_path / "gitops",
        [(END - timedelta(minutes=6), "deploy/feature.yaml", "release demo 2.0")],
    )
    sources = {"changes": {"enabled": True, "git": [GITOPS.model_dump()]}}
    config = project_config(tmp_path, sources=sources)
    hypothesis = config["checks"][0]["hypothesis"]
    hypothesis["evidence_needed"].append("release-changes")
    hypothesis["predictions"].append(
        {"entity_id": "service:demo", "key": "release_changes_30m", "operator": "gt", "value": 0}
    )
    (tmp_path / "lumis.yaml").write_text(json.dumps(config))
    project = YamlProject.from_file(tmp_path / "lumis.yaml")
    incident = Incident.model_validate_json(starter_documents()["incident.json"])
    report = asyncio.run(project.handle_incident(incident, observations=()))
    (fact,) = [item for item in report.context.evidence if item.query_id == "release-changes"]
    assert fact.value == 1 and fact.source == "changes"

    from lumis_sdk.core import IncidentContext
    from lumis_sdk.runtime.session import local_connectors

    tools = InvestigationTools(
        IncidentContext(
            incident=incident, graph=project.config.graph, queries=project.config.queries
        ),
        queries=project.config.queries,
        connectors=local_connectors(project.config, tmp_path, ()),
        settings=project.config.investigator,
        budget=project.config.budget,
        base=tmp_path,
    )
    catalog = json.loads(asyncio.run(tools.inspect(InspectRequest(operation="catalog"))).output)
    assert "changes" in catalog["operations"]
    receipt = asyncio.run(tools.inspect(InspectRequest(operation="changes", target="service:demo")))
    changes = json.loads(receipt.output)["changes"]
    assert receipt.status == "ok" and changes[0]["summary"].startswith("release demo 2.0")
    denied = asyncio.run(tools.inspect(InspectRequest(operation="changes", target="service:x")))
    assert denied.status != "ok"
