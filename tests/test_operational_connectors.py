"""External boundary contracts using real HTTP serialization and deterministic transports."""

import asyncio
import json
from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr
from test_operational_intelligence import fixture

from lumis_sdk.connectors.http import read_json, validate_endpoint
from lumis_sdk.connectors.kubernetes import KubernetesDiscovery, topology_from_kubernetes
from lumis_sdk.connectors.otel import topology_from_otlp
from lumis_sdk.connectors.prometheus import PrometheusConnector
from lumis_sdk.core import IncidentContext, InvestigationBudget
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.models.openrouter import OpenRouterHypothesisModel
from lumis_sdk.reasoning import RuleSource
from lumis_sdk.runtime import InvestigationRuntime


def test_kubernetes_normalizes_selectors_and_owners_without_secret_fields():
    snapshot = topology_from_kubernetes(
        {
            "items": [
                {
                    "kind": "Service",
                    "metadata": {"name": "feature", "namespace": "demo-estate"},
                    "spec": {"selector": {"app": "feature"}},
                },
                {
                    "kind": "Pod",
                    "metadata": {
                        "name": "feature-1",
                        "namespace": "demo-estate",
                        "labels": {"app": "feature", "app.kubernetes.io/name": "feature"},
                        "ownerReferences": [{"kind": "ReplicaSet", "name": "feature-rs"}],
                    },
                    "spec": {"containers": [{"env": [{"value": "must-not-export"}]}]},
                },
                {
                    "kind": "ReplicaSet",
                    "metadata": {"name": "feature-rs", "namespace": "demo-estate"},
                },
                {"kind": "Secret", "metadata": {"name": "secret", "namespace": "demo-estate"}},
                {"kind": "Pod", "metadata": {"name": "other", "namespace": "other"}},
            ]
        },
        namespace="demo-estate",
    )
    assert len(snapshot.entities) == 3
    assert {edge.kind for edge in snapshot.relationships} == {"routes_to", "owns"}
    assert "must-not-export" not in snapshot.model_dump_json()
    assert "secret" not in snapshot.model_dump_json()
    with pytest.raises(ValueError):
        KubernetesDiscovery(namespace="--all-namespaces", context="kind-demo-estate")


def test_prometheus_uses_only_registered_query_and_incident_time():
    project, incident, _ = fixture()
    query = project.queries[2].model_copy(
        update={
            "provider": "prometheus",
            "parameters": {"promql": "sum(demo-estate_db_read_ratio)"},
        }
    )

    def handle(request):
        assert request.method == "GET"
        assert request.url.path == "/api/v1/query"
        assert request.url.params["query"] == "sum(demo-estate_db_read_ratio)"
        assert float(request.url.params["time"]) == incident.ended_at.timestamp()
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [{"metric": {}, "value": [incident.ended_at.timestamp(), "16"]}],
                },
            },
        )

    async def collect():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await PrometheusConnector("http://localhost:9090", client).collect(
                query, incident
            )

    result = asyncio.run(collect())
    assert result[0].value == 16.0
    assert result[0].query_id == query.id


@pytest.mark.parametrize("result", [[], [{"value": [1, "1"]}, {"value": [1, "2"]}]])
def test_prometheus_ambiguous_vector_does_not_invent_aggregation(result):
    project, incident, _ = fixture()
    query = project.queries[2].model_copy(update={"parameters": {"promql": "up"}})

    async def collect():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"status": "success", "data": {"resultType": "vector", "result": result}},
                )
            )
        ) as client:
            return await PrometheusConnector("http://localhost:9090", client).collect(
                query, incident
            )

    with pytest.raises(ValueError, match="exactly one"):
        asyncio.run(collect())


def test_openrouter_structured_output_and_no_tool_authority():
    project, incident, _ = fixture()
    context = IncidentContext(incident=incident, graph=project.graph, queries=project.queries)

    def handle(request):
        payload = json.loads(request.content)
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["provider"] == {"require_parameters": True}
        assert payload["max_tokens"] == 1000
        assert "tools" not in payload
        assert "private-key" not in request.content.decode()
        assert request.headers["authorization"] == "Bearer private-key"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "hypotheses": [
                                        item.model_dump(mode="json")
                                        for item in project.rule_hypotheses
                                    ]
                                }
                            ),
                        },
                    }
                ]
            },
        )

    async def generate():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await OpenRouterHypothesisModel(
                model="test/model",
                api_key=SecretStr("private-key"),
                client=client,
                max_output_tokens=1000,
            ).generate(context)

    assert asyncio.run(generate()) == project.rule_hypotheses


def test_http_reads_refuse_redirects_and_oversized_bodies():
    async def read(response):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: response)
        ) as client:
            return await read_json(client, "GET", "https://example.test", max_bytes=10)

    with pytest.raises(ValueError, match="byte budget"):
        asyncio.run(read(httpx.Response(200, content=b'{"payload": "too long"}')))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(read(httpx.Response(302, headers={"Location": "https://other.test"})))
    with pytest.raises(ValueError):
        validate_endpoint("http://user:password@example.test")


def test_timeout_abstains_and_keeps_query_audit():
    project, incident, _ = fixture()

    class SlowConnector:
        async def collect(self, query, incident):
            await asyncio.sleep(1)
            return ()

    result = asyncio.run(
        InvestigationRuntime(
            graph=OperationalGraph(project.graph),
            sources=[RuleSource(project.rule_hypotheses)],
            queries=project.queries,
            connectors={"snapshot": SlowConnector()},
            budget=InvestigationBudget(query_timeout_seconds=0.001),
        ).investigate(incident)
    )
    assert result.outcome == "abstained"
    assert all(step.status == "timeout" for step in result.trace if step.kind == "query")


def test_incident_window_and_empty_graph_fail_at_boundary():
    project, incident, _ = fixture()
    with pytest.raises(ValueError):
        type(incident).model_validate(
            incident.model_dump()
            | {
                "ended_at": incident.started_at - timedelta(seconds=1),
            }
        )
    with pytest.raises(ValueError, match="absent"):
        IncidentContext(
            incident=incident, graph=project.graph.model_copy(update={"entities": ()}), queries=()
        )


def test_otlp_joins_only_same_trace_parents_and_preserves_dependency_direction():
    def resource(name, spans):
        return {
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": name}},
                    {"key": "service.namespace", "value": {"stringValue": "demo-estate"}},
                    {"key": "private", "value": {"stringValue": "do-not-export"}},
                ]
            },
            "scopeSpans": [{"spans": spans}],
        }

    payload = {
        "resourceSpans": [
            resource("forecast", [{"traceId": "t", "spanId": "parent"}]),
            resource(
                "features",
                [
                    {"traceId": "t", "spanId": "child", "parentSpanId": "parent"},
                    {"traceId": "other", "spanId": "other", "parentSpanId": "parent"},
                ],
            ),
        ]
    }
    graph = topology_from_otlp(payload)
    assert len(graph.relationships) == 1
    assert graph.relationships[0].source == "service:demo-estate:features"
    assert graph.relationships[0].target == "service:demo-estate:forecast"
    assert "do-not-export" not in graph.model_dump_json()
    with pytest.raises(ValueError, match="budget"):
        topology_from_otlp(payload, max_spans=1)


def test_total_deadline_retains_abstention_and_selected_query():
    project, incident, _ = fixture()

    class Slow:
        async def collect(self, query, incident):
            await asyncio.sleep(1)
            return ()

    result = asyncio.run(
        InvestigationRuntime(
            graph=OperationalGraph(project.graph),
            queries=project.queries,
            sources=[RuleSource(project.rule_hypotheses)],
            connectors={"snapshot": Slow()},
            budget=InvestigationBudget(total_timeout_seconds=0.001, query_timeout_seconds=1),
        ).investigate(incident, initial_query_ids=project.initial_query_ids)
    )
    assert result.outcome == "abstained"
    assert result.stop_reason == "deadline_exceeded"
    assert result.trace[0].reference == "database-health"
    assert result.trace[0].status == "timeout"
