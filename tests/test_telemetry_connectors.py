"""Independent Loki/Tempo/Prefect wire contracts, safety boundaries and public YAML wiring."""

import asyncio
import base64
import json
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from test_operational_intelligence import fixture

from lumis_sdk.connectors.loki import LokiConnector
from lumis_sdk.connectors.prefect import PrefectConnector
from lumis_sdk.connectors.settings import LokiSource, PrefectSource, TempoSource
from lumis_sdk.connectors.tempo import TempoConnector
from lumis_sdk.core import EvidenceQuery
from lumis_sdk.investigation.contracts import AgentOutput, InspectRequest
from lumis_sdk.runtime import YamlProject
from lumis_sdk.runtime.discovery import DiscoveryError
from lumis_sdk.runtime.project import OperationalProject

TRACE = "abcdef0123456789abcdef0123456789"
FLOW = "11111111-1111-4111-8111-111111111111"
TASK = "22222222-2222-4222-8222-222222222222"
TASK2 = "33333333-3333-4333-8333-333333333333"
EXAMPLE = Path(__file__).parents[1] / "docs/examples/telemetry-project.yaml"


def incident():
    return fixture()[1]


def query(provider, **parameters):
    return EvidenceQuery(
        id="observation",
        provider=provider,
        entity_id="batch-pipeline",
        key="observation",
        description="Approved observation",
        parameters=parameters,
    )


def ns(at):
    return str(int(at.timestamp()) * 1_000_000_000 + at.microsecond * 1000)


def loki(message="error: forecast failed", at=None):
    return {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"private": "never-export"},
                    "values": [
                        [
                            ns(at or incident().started_at),
                            message,
                        ]
                    ],
                },
            ],
        },
    }


def search():
    return {
        "traces": [
            {
                "traceID": TRACE,
                "startTimeUnixNano": ns(incident().started_at),
                "durationMs": 500,
                "rootServiceName": "forecast",
                "rootTraceName": "build",
                "private": "never-export",
            }
        ]
    }


def trace(encoded=False):
    def identifier(value):
        return base64.b64encode(bytes.fromhex(value)).decode() if encoded else value

    def resource(name, span, parent=None):
        return {
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": name}},
                    {"key": "service.namespace", "value": {"stringValue": "demo-estate"}},
                    {"key": "authorization", "value": {"stringValue": "never-export"}},
                ]
            },
            "scopeSpans": [
                {
                    "spans": [
                        {
                            "traceId": identifier(TRACE),
                            "spanId": identifier(span),
                            "parentSpanId": identifier(parent) if parent else "",
                            "name": "build",
                            "startTimeUnixNano": ns(incident().started_at),
                            "endTimeUnixNano": ns(incident().started_at + timedelta(seconds=1)),
                            "attributes": [
                                {"key": "db.statement", "value": {"stringValue": "secret"}}
                            ],
                        }
                    ]
                }
            ],
        }

    return {
        "batches": [
            resource("forecast", "abcdef0123456789"),
            resource("features", "fedcba9876543210", "abcdef0123456789"),
        ]
    }


def run(identity=FLOW, *, task=False):
    return {
        "id": identity,
        "flow_run_id": FLOW,
        "name": "feature-build" if task else "forecast",
        "start_time": incident().started_at.isoformat(),
        "end_time": None,
        "total_run_time": 1.25,
        "state": {
            "type": "FAILED",
            "timestamp": (incident().started_at + timedelta(seconds=1)).isoformat(),
        },
        "parameters": {"api_key": "never-export"},
        "task_inputs": {},
    }


def collect(connector_type, source, registered, payload, handle=None):
    async def execute():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                handle or (lambda request: httpx.Response(200, json=payload))
            )
        ) as client:
            result = await connector_type(source, client).collect(registered, incident())
            assert not client.is_closed
            return result

    return asyncio.run(execute())


def test_loki_wire_window_redaction_and_count(monkeypatch):
    monkeypatch.setenv("LOG_AUTH", "Bearer private-token")
    source = LokiSource(
        enabled=True, endpoint="http://loki.test", headers_env={"Authorization": "LOG_AUTH"}
    )
    registered = query("loki", logql='{service_name="forecast"} |= "error"')

    def handle(request):
        assert request.method == "GET"
        assert request.url.path == "/loki/api/v1/query_range"
        assert request.url.params["query"] == registered.parameters["logql"]
        assert request.url.params["start"] == incident().started_at.isoformat()
        assert request.url.params["end"] == incident().ended_at.isoformat()
        assert request.url.params["limit"] == "50"
        assert request.headers["Authorization"] == "Bearer private-token"
        return httpx.Response(200, json=loki("error: private-token password=hidden"))

    result = collect(LokiConnector, source, registered, None, handle)
    assert "private-token" not in result[0].value
    assert "hidden" not in result[0].value
    assert "never-export" not in result[0].value
    count = collect(
        LokiConnector, source, query("loki", logql='{job="forecast"}', output="count"), loki()
    )
    assert count[0].value == 1 and count[0].quality == "observed"


@pytest.mark.parametrize("provider", ["loki", "tempo", "prefect"])
def test_empty_results_never_invent_zero_or_false(provider):
    sources = {
        "loki": LokiSource(enabled=True, endpoint="http://loki.test"),
        "tempo": TempoSource(enabled=True, endpoint="http://tempo.test"),
        "prefect": PrefectSource(
            enabled=True, endpoint="http://prefect.test/api", flow_names=("forecast",)
        ),
    }
    params = {
        "loki": {"logql": '{job="forecast"}', "output": "count"},
        "tempo": {"traceql": '{ resource.service.name = "forecast" }'},
        "prefect": {"flow_name": "forecast", "output": "failed_count"},
    }
    payloads = {
        "loki": {"status": "success", "data": {"resultType": "streams", "result": []}},
        "tempo": {"traces": []},
        "prefect": [],
    }
    classes = {"loki": LokiConnector, "tempo": TempoConnector, "prefect": PrefectConnector}
    assert (
        collect(
            classes[provider],
            sources[provider],
            query(provider, **params[provider]),
            payloads[provider],
        )
        == ()
    )


def test_tempo_search_duration_and_exact_trace_spans():
    source = TempoSource(enabled=True, endpoint="http://tempo.test")

    def handle(request):
        assert request.method == "GET" and request.url.path == "/api/search"
        assert request.url.params["start"] == str(int(incident().started_at.timestamp()))
        assert request.url.params["end"] == str(int(incident().ended_at.timestamp()) + 1)
        return httpx.Response(200, json=search())

    facts = collect(
        TempoConnector,
        source,
        query("tempo", traceql='{ resource.service.name = "forecast" }', output="duration_ms"),
        None,
        handle,
    )
    assert facts[0].value == 500.0
    for encoded in (False, True):
        facts = collect(
            TempoConnector, source, query("tempo", trace_id=TRACE, output="spans"), trace(encoded)
        )
        assert len(facts) == 2
        assert "never-export" not in facts[0].value and "db.statement" not in facts[0].value


def test_tempo_normalizes_unpadded_search_ids_to_otlp_identity():
    payload = trace()
    padded = "0" + TRACE[1:]
    for resource in payload["batches"]:
        resource["scopeSpans"][0]["spans"][0]["traceId"] = padded

    def handle(request):
        assert request.url.path == "/api/traces/" + padded
        return httpx.Response(200, json=payload)

    facts = collect(
        TempoConnector,
        TempoSource(enabled=True, endpoint="http://tempo.test"),
        query("tempo", trace_id=padded.lstrip("0"), output="spans"),
        None,
        handle,
    )
    assert len(facts) == 2


def test_approved_traceql_can_fetch_spans_with_no_preconfigured_incident_trace_id():
    paths = []

    def handle(request):
        paths.append(request.url.path)
        if request.url.path == "/api/search":
            assert request.url.params["limit"] == "5"
            return httpx.Response(200, json=search())
        assert request.url.path == "/api/traces/" + TRACE
        return httpx.Response(200, json=trace(True))

    source = TempoSource(enabled=True, endpoint="http://tempo.test")
    registered = query("tempo", traceql='{ resource.service.name = "forecast" }', output="spans")
    facts = collect(TempoConnector, source, registered, None, handle)
    assert len(paths) == 2 and len(facts) == 2
    assert len({item.id for item in facts}) == 2
    facts = collect(
        TempoConnector,
        source.model_copy(update={"max_trace_reads": 1}),
        registered,
        None,
        lambda request: httpx.Response(
            200, json=search() if request.url.path == "/api/search" else trace()
        ),
    )
    assert all(item.quality == "degraded" for item in facts)


def test_prefect_read_only_filters_and_seconds_to_milliseconds():
    source = PrefectSource(
        enabled=True, endpoint="http://prefect.test/api", flow_names=("forecast",)
    )

    def handle(request):
        assert request.method == "POST" and request.url.path == "/api/flow_runs/filter"
        body = json.loads(request.content)
        assert body["flows"] == {"name": {"any_": ["forecast"]}}
        assert body["flow_runs"]["start_time"] == {
            "after_": incident().started_at.isoformat(),
            "before_": incident().ended_at.isoformat(),
        }
        assert body["limit"] == 50 and body["offset"] == 0
        return httpx.Response(200, json=[run()])

    facts = collect(
        PrefectConnector,
        source,
        query("prefect", flow_name="forecast", output="max_duration_ms"),
        None,
        handle,
    )
    assert facts[0].value == 1250.0
    facts = collect(PrefectConnector, source, query("prefect", flow_name="forecast"), [run()])
    assert "never-export" not in facts[0].value
    assert "FAILED" in facts[0].value


@pytest.mark.parametrize("provider", ["loki", "tempo", "prefect"])
def test_caps_degrade_and_overflow_fails(provider):
    classes = {"loki": LokiConnector, "tempo": TempoConnector, "prefect": PrefectConnector}
    sources = {
        "loki": LokiSource(enabled=True, endpoint="http://loki.test", max_results=1),
        "tempo": TempoSource(enabled=True, endpoint="http://tempo.test", max_results=1),
        "prefect": PrefectSource(
            enabled=True,
            endpoint="http://prefect.test/api",
            max_results=1,
            flow_names=("forecast",),
        ),
    }
    queries = {
        "loki": query("loki", logql='{job="forecast"}', output="count"),
        "tempo": query("tempo", traceql='{ resource.service.name = "forecast" }'),
        "prefect": query("prefect", flow_name="forecast", output="failed_count"),
    }
    payload = {"loki": loki(), "tempo": search(), "prefect": [run()]}[provider]
    assert (
        collect(classes[provider], sources[provider], queries[provider], payload)[0].quality
        == "degraded"
    )
    if provider == "loki":
        payload["data"]["result"][0]["values"] *= 2
    elif provider == "tempo":
        payload["traces"] *= 2
    else:
        payload.append(run(TASK))
    with pytest.raises(ValueError):
        collect(classes[provider], sources[provider], queries[provider], payload)


@pytest.mark.parametrize(
    "case",
    [
        "loki-time",
        "tempo-duration-window",
        "tempo-time",
        "prefect-state-time",
        "trace-id",
        "nan",
        "duplicate",
        "task-scope",
        "partial",
    ],
)
def test_invalid_observations_fail_closed(case):
    if case.startswith("loki") or case == "partial":
        source = LokiSource(enabled=True, endpoint="http://loki.test")
        registered = query("loki", logql='{job="forecast"}')
        payload = (
            loki(at=incident().ended_at + timedelta(seconds=1)) if case == "loki-time" else loki()
        )
        if case == "partial":
            payload["warnings"] = ["partial response"]
        connector = LokiConnector
    elif case.startswith("prefect") or case == "task-scope":
        source = PrefectSource(
            enabled=True, endpoint="http://prefect.test/api", flow_names=("forecast",)
        )
        registered = query("prefect", flow_name="forecast")
        payload = [run()]
        if case == "task-scope":
            registered = query(
                "prefect", flow_name="forecast", operation="task_runs", flow_run_id=TASK
            )
        else:
            payload[0]["state"]["timestamp"] = (
                incident().ended_at + timedelta(seconds=1)
            ).isoformat()
        connector = PrefectConnector
    else:
        source = TempoSource(enabled=True, endpoint="http://tempo.test")
        registered = query("tempo", traceql='{ resource.service.name = "forecast" }')
        payload = search()
        connector = TempoConnector
        if case == "tempo-time":
            payload["traces"][0]["startTimeUnixNano"] = ns(
                incident().ended_at + timedelta(seconds=1)
            )
        elif case == "tempo-duration-window":
            payload["traces"][0]["durationMs"] = 3_600_000
        elif case == "nan":
            payload["traces"][0]["durationMs"] = "NaN"
        elif case == "duplicate":
            payload["traces"] *= 2
        else:
            registered = query("tempo", trace_id=TRACE, output="spans")
            payload = trace()
            payload["batches"][0]["scopeSpans"][0]["spans"][0]["traceId"] = "f" * 32
    with pytest.raises(ValueError):
        collect(connector, source, registered, payload)


@pytest.mark.parametrize("source", [LokiSource, TempoSource, PrefectSource])
def test_remote_sources_reject_unsafe_endpoints(source):
    for endpoint in ("file:///etc/passwd", "http://user:secret@localhost", "http://localhost?a=b"):
        with pytest.raises(ValueError):
            source(enabled=True, endpoint=endpoint)


def test_yaml_query_scope_and_extra_parameters_fail_before_io():
    project = YamlProject.from_file(EXAMPLE).config
    for provider, updates in (
        ("loki", {"logql": '{} |= "error"'}),
        ("tempo", {"traceql": "{ status = error }"}),
        ("prefect", {"flow_name": "unapproved"}),
    ):
        payload = project.model_dump()
        entry = next(item for item in payload["queries"] if item["provider"] == provider)
        entry["parameters"] = updates
        with pytest.raises(ValueError):
            OperationalProject.model_validate(payload)
        entry["parameters"]["endpoint"] = "http://unapproved.test"
        with pytest.raises(ValueError):
            OperationalProject.model_validate(payload)


def test_yaml_handle_incident_agent_receipts_share_live_connectors():
    session = YamlProject.from_file(EXAMPLE)
    event = incident().model_copy(update={"affected_entities": ("service:demo-estate:forecast",)})
    calls = []

    def handle(request):
        calls.append(request.url.path)
        assert "Authorization" not in request.headers
        payload = {
            "/loki/api/v1/query_range": loki(),
            "/api/search": search(),
            "/api/flow_runs/filter": [run()],
        }[request.url.path]
        return httpx.Response(200, json=payload)

    class Investigator:
        async def investigate(self, tools, findings):
            receipt = await tools.inspect(
                InspectRequest(operation="evidence", query_id="forecast-errors")
            )
            assert receipt.status == "ok" and "forecast failed" in receipt.output
            return AgentOutput(unresolved_questions=("Needs independent review",))

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            report = await session.handle_incident(
                event, client=client, investigator=Investigator()
            )
            assert not client.is_closed
            return report

    report = asyncio.run(execute())
    assert {item.source for item in report.context.evidence} == {"loki", "tempo", "prefect"}
    assert len(calls) == 3  # Cached agent inspection does not make a second log request.
    assert report.truth_state == "unconfirmed_hypothesis" and report.requires_human_review
    assert report.stop_reason == "agent_completed"


def test_native_agent_dynamically_collects_all_registered_http_providers():
    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    from lumis_sdk.investigation.agent import PydanticInvestigator

    session = YamlProject.from_file(EXAMPLE)
    payload = session.config.model_dump()
    payload["initial_query_ids"] = []
    session = YamlProject(OperationalProject.model_validate(payload), session.base)
    event = incident().model_copy(update={"affected_entities": ("service:demo-estate:forecast",)})
    calls = []

    def model(messages, info):
        index = len(calls)
        calls.append(messages)
        if index < 3:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "inspect",
                        {
                            "request": {
                                "operation": "evidence",
                                "query_id": session.config.queries[index].id,
                            }
                        },
                        tool_call_id=f"inspect-{index}",
                    )
                ]
            )
        assert "forecast failed" in str(messages) and "FAILED" in str(messages)
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {"unresolved_questions": ["Review independently"]},
                    tool_call_id="report",
                )
            ]
        )

    def handle(request):
        return httpx.Response(
            200,
            json={
                "/loki/api/v1/query_range": loki(),
                "/api/search": search(),
                "/api/flow_runs/filter": [run()],
            }[request.url.path],
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await session.handle_incident(
                event, client=client, investigator=PydanticInvestigator(FunctionModel(model))
            )

    report = asyncio.run(execute())
    assert report.stop_reason == "agent_completed"
    assert report.metrics.model_requests == 4 and report.metrics.evidence_queries == 3
    assert {item.source for item in report.context.evidence} == {"loki", "tempo", "prefect"}


def test_discovery_request_entity_and_edge_bounds():
    async def execute(source, **bounds):
        def handle(request):
            return httpx.Response(
                200,
                json=[run()]
                if request.url.path.endswith("flow_runs/filter")
                else [run(TASK, task=True)],
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await PrefectConnector(source, client).discover(at=incident().ended_at, **bounds)

    source = PrefectSource(
        enabled=True,
        endpoint="http://prefect.test/api",
        flow_names=("forecast",),
        discover_topology=True,
        namespace="demo-estate",
    )
    with pytest.raises(ValueError, match="request budget"):
        asyncio.run(execute(source.model_copy(update={"max_requests": 1})))
    with pytest.raises(ValueError, match="entity budget"):
        asyncio.run(execute(source, max_entities=1))
    with pytest.raises(ValueError, match="relationship budget"):
        asyncio.run(execute(source, max_relationships=1))


def test_topology_discovery_prefect_dependencies_and_tempo_trace_identity():
    config = YamlProject.from_file(EXAMPLE).config.model_dump()
    config["sources"]["prefect"].update(discover_topology=True, namespace="demo-estate")
    config["sources"]["tempo"].update(
        discovery_query='{ resource.service.namespace = "demo-estate" }',
        service_namespace="demo-estate",
    )
    task2 = run(TASK2, task=True)
    task2["task_inputs"] = {"data": [{"input_type": "task_run", "id": TASK}]}

    def handle(request):
        if request.url.path.endswith("flow_runs/filter"):
            return httpx.Response(200, json=[run()])
        if request.url.path.endswith("task_runs/filter"):
            assert json.loads(request.content)["flow_runs"] == {"id": {"any_": [FLOW]}}
            assert json.loads(request.content)["sort"] == "EXPECTED_START_TIME_ASC"
            return httpx.Response(200, json=[run(TASK, task=True), task2])
        return httpx.Response(
            200, json=search() if request.url.path == "/api/search" else trace(True)
        )

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await YamlProject(
                OperationalProject.model_validate(config), EXAMPLE.parent
            ).prepare(at=incident().ended_at, client=client)

    prepared = asyncio.run(execute())
    graph = prepared.discovery.graph
    assert any(
        edge.source == "prefect:task-run:" + TASK
        and edge.target == "prefect:task-run:" + TASK2
        and edge.kind == "feeds"
        for edge in graph.relationships
    )
    assert any(
        edge.source == "service:demo-estate:features"
        and edge.target == "service:demo-estate:forecast"
        for edge in graph.relationships
    )
    assert "never-export" not in graph.model_dump_json()
    assert all(
        source.status == "ok"
        for source in prepared.discovery.sources
        if source.name in {"tempo", "prefect"}
    )


def test_discovery_failure_is_not_usable_partial_graph():
    config = YamlProject.from_file(EXAMPLE).config.model_dump()
    config["sources"]["prefect"].update(discover_topology=True, namespace="demo-estate")

    async def execute():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(403, text="secret"))
        ) as client:
            return await YamlProject(
                OperationalProject.model_validate(config), EXAMPLE.parent
            ).prepare(at=incident().ended_at, client=client)

    with pytest.raises(DiscoveryError) as error:
        asyncio.run(execute())
    assert not error.value.report.complete
    assert "secret" not in error.value.report.model_dump_json()


def test_unknown_prefect_state_cannot_become_zero_failures():
    payload = run()
    payload["state"]["type"] = "INVALID_STATE"
    with pytest.raises(ValueError, match="unknown Prefect state"):
        collect(
            PrefectConnector,
            PrefectSource(
                enabled=True, endpoint="http://prefect.test/api", flow_names=("forecast",)
            ),
            query("prefect", flow_name="forecast", output="failed_count"),
            [payload],
        )


def test_discovery_http_read_obeys_project_byte_budget():
    payload = YamlProject.from_file(EXAMPLE).config.model_dump()
    payload["sources"]["prefect"].update(discover_topology=True, namespace="demo-estate")
    payload["discovery"]["max_response_bytes"] = 1

    async def execute():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[run()]))
        ) as client:
            return await YamlProject(
                OperationalProject.model_validate(payload), EXAMPLE.parent
            ).prepare(at=incident().ended_at, client=client)

    with pytest.raises(DiscoveryError):
        asyncio.run(execute())


def test_missing_auth_byte_limit_redirect_and_span_budget(monkeypatch):
    monkeypatch.delenv("MISSING_AUTH", raising=False)
    registered = query("loki", logql='{job="forecast"}')
    with pytest.raises(ValueError, match="credential"):
        collect(
            LokiConnector,
            LokiSource(
                enabled=True,
                endpoint="http://loki.test",
                headers_env={"Authorization": "MISSING_AUTH"},
            ),
            registered,
            loki(),
        )
    with pytest.raises(ValueError, match="byte budget"):
        collect(
            LokiConnector,
            LokiSource(enabled=True, endpoint="http://loki.test", max_response_bytes=10),
            registered,
            loki(),
        )
    with pytest.raises(httpx.HTTPStatusError):
        collect(
            LokiConnector,
            LokiSource(enabled=True, endpoint="http://loki.test"),
            registered,
            None,
            lambda request: httpx.Response(302, headers={"Location": "http://other.test"}),
        )
    with pytest.raises(ValueError, match="span budget"):
        collect(
            TempoConnector,
            TempoSource(enabled=True, endpoint="http://tempo.test", max_spans=1),
            query("tempo", trace_id=TRACE, output="spans"),
            trace(),
        )
