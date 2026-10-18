"""Portable maintenance regressions: synthetic facts, scripted models and no remote calls."""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_incident_agent import broker, estate
from typer.testing import CliRunner

from lumis_sdk import core
from lumis_sdk.cli.app import app
from lumis_sdk.core import Check, Entity, GraphSnapshot
from lumis_sdk.core.contracts import validate_hypothesis_catalog
from lumis_sdk.core.warnings import hypothesis_warnings, numeric_overlap
from lumis_sdk.investigation.agent import INSTRUCTIONS, PydanticInvestigator
from lumis_sdk.investigation.config import InvestigatorSettings
from lumis_sdk.investigation.contracts import InspectRequest, RunMetrics
from lumis_sdk.investigation.providers import configured_investigator
from lumis_sdk.reasoning import assess
from lumis_sdk.runtime.project import ModelSettings, OperationalProject


def test_inspection_classifies_invalid_denied_unavailable_and_redacts(tmp_path):
    project, event, _ = estate(tmp_path)
    settings = InvestigatorSettings.model_validate(
        {
            "repositories": [
                {
                    "id": "source",
                    "root": str(tmp_path),
                    "entity_ids": ["service:demo"],
                    "files": ["missing.py"],
                }
            ]
        }
    )
    tools = broker(project, event, settings=settings)

    async def run():
        invalid = await tools.inspect(InspectRequest(operation="code.read", target="source"))
        denied = await tools.inspect(
            InspectRequest(operation="code.read", target="source", path="not-approved.py")
        )
        missing = await tools.inspect(
            InspectRequest(operation="code.read", target="source", path="missing.py")
        )
        assert (invalid.status, invalid.reason_code) == ("denied", "invalid_request")
        assert (denied.status, denied.reason_code) == ("denied", "access_denied")
        assert (missing.status, missing.reason_code) == ("error", "source_unavailable")
        assert str(tmp_path) not in missing.model_dump_json()

    asyncio.run(run())


@pytest.mark.parametrize("failure", ["error", "timeout", "empty"])
def test_cached_query_retains_outcome_without_hidden_retry(tmp_path, failure):
    project, event, _ = estate(tmp_path)
    tools = broker(project, event)

    class Source:
        count = 0

        async def collect(self, query, incident):
            self.count += 1
            if failure == "timeout":
                raise TimeoutError("password=hunter2secret")
            if failure == "error":
                raise RuntimeError("password=hunter2secret https://private.test")
            return ()

    source = Source()
    tools.connectors["snapshot"] = source

    async def run():
        first = await tools.collect("health")
        second = await tools.collect("health")
        expected = "ok" if failure == "empty" else failure
        assert first.status == second.status == expected
        assert second.reason_code == first.reason_code
        assert second.cached_from == first.id
        assert source.count == 1 and not tools.context.evidence
        assert "hunter2secret" not in second.model_dump_json()
        if failure == "empty":
            assert second.output == "[]"

    asyncio.run(run())


def test_receipt_full_digest_visible_digest_and_empty_budget(tmp_path):
    project, event, _ = estate(tmp_path)
    settings = InvestigatorSettings.model_validate(
        {"budget": {"max_tool_characters": 100, "max_total_tool_characters": 100}}
    )
    tools = broker(project, event, settings=settings)
    raw = "x" * 500
    first = tools._receipt("code.read", "Approved synthetic text", raw)
    second = tools._receipt("code.read", "Approved synthetic text", raw)
    assert first.original_characters == 500 and first.truncated
    assert first.digest == hashlib.sha256(raw.encode()).hexdigest()
    assert first.output_digest == hashlib.sha256(first.output.encode()).hexdigest()
    assert first.digest != first.output_digest
    assert second.truncated and second.output == ""
    assert second.output_digest == hashlib.sha256(b"").hexdigest()
    tools = broker(project, event)
    structural = "a" * 40 + " 2026-10-03T12:00:00+00:00\n"
    log = tools._receipt("git.log", "Validated structural Git metadata", structural)
    assert log.output == structural and not log.truncated


@pytest.mark.parametrize(
    "left,right,expected",
    [
        (("gt", 100), ("gt", 0), True),
        (("gt", 100), ("le", 100), False),
        (("ge", 100), ("le", 100), True),
        (("eq", 100), ("ne", 100), False),
        (("ne", 0), ("lt", 0), True),
        (("lt", 0), ("ge", 0), False),
        (("eq", True), ("ne", False), False),
        (("eq", "x"), ("eq", "x"), False),
    ],
)
def test_numeric_overlap_warning_boundaries(left, right, expected):
    def check(pair):
        return Check(entity_id="service", key="x", operator=pair[0], value=pair[1])

    assert numeric_overlap(check(left), check(right)) is expected


def test_overlap_warns_without_changing_assessment_and_path_edges_not_validated(tmp_path):
    project, event, facts = estate(tmp_path)
    original = project.config.checks[0].hypothesis
    hypothesis = original.model_copy(
        update={
            "predictions": (
                Check(entity_id="service:demo", key="healthy", operator="eq", value=1),
            ),
            "falsifiers": (Check(entity_id="service:demo", key="healthy", operator="gt", value=0),),
        }
    )
    assert hypothesis_warnings(hypothesis)
    tools = broker(project, event, facts=tuple(f.model_copy(update={"value": 1}) for f in facts))
    asyncio.run(tools.collect("health"))
    assert assess(hypothesis, tools.context, ("test",)).state == "contradicted"
    graph = GraphSnapshot(
        entities=(
            *project.config.graph.entities,
            Entity(id="unconnected", kind="service", name="Unconnected"),
        )
    )
    skipped = original.model_copy(update={"causal_path": ("unconnected", "service:demo")})
    validate_hypothesis_catalog(skipped, graph, project.config.queries)


def test_upfront_shared_queries_fetch_once_and_glossary_covers_contracts(tmp_path):
    project, event, facts = estate(tmp_path)
    config = project.config.model_dump()
    config["checks"] = (*config["checks"], config["checks"][0] | {"id": "second-rule"})
    project = type(project)(OperationalProject.model_validate(config), tmp_path)
    report = asyncio.run(project.handle_incident(event, observations=facts))
    assert report.metrics.evidence_queries == 1 and len(report.receipts) == 1
    glossary = (Path(__file__).parents[1] / "docs/glossary.md").read_text()
    assert all(f"`{name}`" in glossary for name in core.__all__)


def test_named_tools_catalog_and_provisional_states_without_catalog_roundtrip(tmp_path):
    project, event, facts = estate(tmp_path)
    config = project.config.model_dump()
    config.update(checks=[], initial_query_ids=[])
    project = type(project)(OperationalProject.model_validate(config), tmp_path)
    hypothesis = estate(tmp_path)[0].config.checks[0].hypothesis
    calls = []

    def model(messages, info):
        calls.append(messages)
        if len(calls) == 1:
            assert "Scoped tool catalog" in str(messages) and "health" in str(messages)
            assert "evidence_query" in {tool.name for tool in info.function_tools}
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "register_hypothesis", {"hypothesis": hypothesis.model_dump(mode="json")}
                    )
                ]
            )
        if len(calls) == 2:
            return ModelResponse(parts=[ToolCallPart("evidence_query", {"query_id": "health"})])
        returned = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart) and part.tool_name == "evidence_query"
        ][-1]
        assert returned.content.assessments[0].state == "supported"
        assert returned.content.assessments[0].supporting_evidence_ids == ("demo-health",)
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name, {"hypotheses": [hypothesis.model_dump(mode="json")]}
                )
            ]
        )

    report = asyncio.run(
        project.handle_incident(
            event, observations=facts, investigator=PydanticInvestigator(FunctionModel(model))
        )
    )
    assert report.stop_reason == "agent_completed" and report.metrics.tool_attempts == 2
    assert report.metrics.model_requests == 3
    assert not any(receipt.operation == "catalog" for receipt in report.receipts)


def test_proposal_rounds_and_explicit_refusal(tmp_path):
    project, event, facts = estate(tmp_path)
    tools = broker(
        project,
        event,
        facts=facts,
        settings=InvestigatorSettings.model_validate(
            {"budget": {"initial_candidates": 2, "followup_candidates": 1}}
        ),
    )
    hypothesis = project.config.checks[0].hypothesis

    async def run():
        for name in ("h1", "h2"):
            assert (
                await tools.inspect(
                    InspectRequest(
                        operation="hypothesis.register",
                        hypothesis=hypothesis.model_copy(update={"id": name}),
                    )
                )
            ).status == "ok"
        refused = await tools.inspect(
            InspectRequest(
                operation="hypothesis.register",
                hypothesis=hypothesis.model_copy(update={"id": "h3"}),
            )
        )
        assert refused.reason_code == "proposal_limit" and "Assess" in refused.output
        await tools.collect("health")
        allowed = await tools.inspect(
            InspectRequest(
                operation="hypothesis.register",
                hypothesis=hypothesis.model_copy(update={"id": "h3"}),
            )
        )
        assert allowed.status == "ok"
        refused = await tools.inspect(
            InspectRequest(
                operation="hypothesis.register",
                hypothesis=hypothesis.model_copy(update={"id": "h4"}),
            )
        )
        assert refused.reason_code == "proposal_limit" and "report" in refused.output
        assert len(tools.candidates) == 3

    asyncio.run(run())


def test_readable_report_cli_alias_and_escaping(tmp_path):
    project, event, facts = estate(tmp_path)
    report = asyncio.run(project.investigate_incident(event, observations=facts))
    assert report == asyncio.run(project.handle_incident(event, observations=facts))
    document = report.markdown()
    assert "Human review required" in document and "#evidence-1" in document
    assert "can't tell" not in document  # The nonterminal health rule matches, but needs review.
    malicious = report.model_copy(
        update={"unresolved_questions": ("<script>alert(1)</script> [click](javascript:alert(1))",)}
    )
    rendered = malicious.markdown()
    assert "<script>" not in rendered and "[click](javascript:" not in rendered
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "incident",
            "--project",
            str(tmp_path / "lumis.yaml"),
            "--incident",
            str(tmp_path / "incident.json"),
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0 and "# Incident" in result.output
    assert "requires\\_human\\_expert" in result.output
    assert (
        runner.invoke(
            app,
            [
                "incident",
                "--project",
                str(tmp_path / "lumis.yaml"),
                "--incident",
                str(tmp_path / "incident.json"),
                "--format",
                "html",
            ],
        ).exit_code
        != 0
    )


def test_cache_settings_metrics_and_timing_instruction():
    config = ModelSettings(
        provider="anthropic",
        model="synthetic-model",
        cache_instructions="5m",
        cache_tool_definitions=True,
    )
    assert config.cache_instructions == "5m"
    with pytest.raises(ValueError, match="Anthropic"):
        ModelSettings(provider="openai", model="synthetic", cache_instructions=True)
    assert RunMetrics().cache_read_share == 0
    assert RunMetrics(input_tokens=100, cache_read_tokens=80).cache_read_share == 0.8
    assert "observation window" in INSTRUCTIONS and "delayed effects" in INSTRUCTIONS


def test_bedrock_offline_construction_no_keys_in_yaml_and_client_closed(monkeypatch):
    import boto3
    from botocore.config import Config

    seen = {}

    class Client:
        closed = False

        def close(self):
            self.closed = True

    client = Client()

    class Session:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def client(self, service, *, config):
            assert service == "bedrock-runtime" and isinstance(config, Config)
            assert config.retries["total_max_attempts"] == 1
            assert config.connect_timeout == config.read_timeout == 2
            seen["config"] = config
            return client

    monkeypatch.setattr(boto3, "Session", Session)
    settings = ModelSettings(
        provider="bedrock", model="anthropic.synthetic-v1:0", aws_region="us-east-1"
    )

    async def run():
        async with configured_investigator(settings, timeout=2) as agent:
            assert agent.agent.model.model_name == settings.model

    asyncio.run(run())
    assert seen["region_name"] == "us-east-1" and client.closed
    with pytest.raises(ValueError, match="credential chain"):
        ModelSettings(provider="bedrock", model="test", api_key_env="SECRET")


def test_scripted_agent_reports_after_proposal_refusal_and_keeps_cache_metrics(tmp_path):
    project, event, facts = estate(tmp_path)
    config = project.config.model_dump()
    config["investigator"]["budget"].update(initial_candidates=1, followup_candidates=0)
    project = type(project)(OperationalProject.model_validate(config), tmp_path)
    hypothesis = project.config.checks[0].hypothesis
    calls = []

    def model(messages, info):
        calls.append(messages)
        if len(calls) <= 2:
            candidate = hypothesis.model_copy(update={"id": f"h{len(calls)}"})
            parts = [ToolCallPart("register_hypothesis", {"hypothesis": candidate.model_dump()})]
        else:
            receipt = messages[-1].parts[0].content
            assert receipt.reason_code == "proposal_limit" and "report" in receipt.output
            parts = [
                ToolCallPart(
                    info.output_tools[0].name,
                    {"hypotheses": [hypothesis.model_copy(update={"id": "h1"}).model_dump()]},
                )
            ]
        return ModelResponse(
            parts=parts,
            usage=RequestUsage(input_tokens=100, output_tokens=10, cache_read_tokens=80),
        )

    report = asyncio.run(
        project.handle_incident(
            event, observations=facts, investigator=PydanticInvestigator(FunctionModel(model))
        )
    )
    assert report.stop_reason == "agent_completed" and len(calls) == 3
    assert len(report.assessments) == 1 and report.assessments[0].hypothesis.id == "h1"
    assert report.metrics.cache_read_tokens == 240 and report.metrics.cache_read_share == 0.8
    # The initial request is an unchanged prefix while tool responses are appended.
    assert all(messages[0] == calls[0][0] for messages in calls)


@pytest.mark.parametrize("mode,expected", [("false", "contradicted"), ("empty", "unresolved")])
def test_provisional_states_include_ruling_out_and_unknown_evidence(tmp_path, mode, expected):
    project, event, facts = estate(tmp_path)
    facts = tuple(f.model_copy(update={"value": True}) for f in facts) if mode == "false" else ()
    tools = broker(project, event, facts=facts)
    tools.register(project.config.checks[0].hypothesis)
    receipt = asyncio.run(tools.collect("health"))
    assert receipt.assessments[0].state == expected
    if expected == "contradicted":
        assert receipt.assessments[0].contradicting_evidence_ids
    else:
        assert receipt.assessments[0].missing_check_count > 0


def test_small_tool_budget_explicitly_omits_candidate_states(tmp_path):
    project, event, facts = estate(tmp_path)
    settings = InvestigatorSettings.model_validate({"budget": {"max_tool_characters": 100}})
    tools = broker(project, event, facts=facts, settings=settings)
    tools.register(project.config.checks[0].hypothesis)
    receipt = asyncio.run(tools.collect("health"))
    assert receipt.assessments_truncated and not receipt.assessments
    assert receipt.truncated and len(receipt.output) <= 100


def test_report_rejects_forged_provisional_evidence_and_cache_links(tmp_path):
    project, event, facts = estate(tmp_path)
    report = asyncio.run(project.handle_incident(event, observations=facts))
    data = report.model_dump()
    data["receipts"] = [r.model_dump() for r in report.receipts]
    data["receipts"][0]["cached_from"] = "unknown"
    with pytest.raises(ValueError, match="earlier receipt"):
        type(report).model_validate(data)
    data["receipts"][0]["cached_from"] = None
    assessment = report.findings[0].assessment
    data["assessments"] = [assessment.model_dump()]
    data["receipts"][0]["assessments"] = [
        {
            "hypothesis_id": assessment.hypothesis.id,
            "state": "supported",
            "supporting_evidence_ids": ["invented-evidence"],
            "missing_check_count": 0,
        }
    ]
    with pytest.raises(ValueError, match="unknown provisional evidence"):
        type(report).model_validate(data)


def test_followup_round_waits_for_all_initial_requested_queries(tmp_path):
    project, event, facts = estate(tmp_path, terminal=True)
    tools = broker(
        project,
        event,
        facts=facts,
        settings=InvestigatorSettings.model_validate(
            {"budget": {"initial_candidates": 1, "followup_candidates": 1}}
        ),
    )
    candidate = project.config.checks[0].hypothesis
    tools.register(candidate)
    asyncio.run(tools.collect("health"))
    assert candidate.id not in tools.assessed_candidates
    with pytest.raises(ValueError, match="Assess the initial"):
        tools.register(candidate.model_copy(update={"id": "followup"}))
    asyncio.run(tools.collect("ready"))
    tools.register(candidate.model_copy(update={"id": "followup"}))
    assert len(tools.candidates) == 2


def test_no_fault_control_is_not_promoted_to_a_diagnosis(tmp_path):
    project, event, facts = estate(tmp_path)
    healthy = tuple(f.model_copy(update={"value": True}) for f in facts)

    def model(messages, info):
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {
                        "unresolved_questions": [
                            "The healthy observation rules out the configured outage signature; "
                            "no cause is established for the caller-reported symptom."
                        ]
                    },
                )
            ]
        )

    report = asyncio.run(
        project.handle_incident(
            event, observations=healthy, investigator=PydanticInvestigator(FunctionModel(model))
        )
    )
    assert report.stop_reason == "agent_completed" and report.conclusion == "insufficient_evidence"
    assert report.findings[0].status == "no_match" and not report.assessments
    assert "did not match (ruled out)" in report.findings[0].display_status
    assert "#evidence-1" in report.markdown() and report.requires_human_review


def test_anthropic_cache_controls_reach_pydantic_wire_and_usage(tmp_path, monkeypatch):
    import httpx2

    project, event, facts = estate(tmp_path)
    seen = []

    def response(request):
        body = json.loads(request.content)
        seen.append(body)
        name = next(tool["name"] for tool in body["tools"] if tool["name"] == "final_result")
        return httpx2.Response(
            200,
            json={
                "id": "synthetic-message",
                "type": "message",
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [{"type": "tool_use", "id": "final", "name": name, "input": {}}],
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "cache_read_input_tokens": 80,
                    "cache_creation_input_tokens": 5,
                },
            },
        )

    original = httpx2.AsyncClient

    class OfflineClient(original):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx2.MockTransport(response), **kwargs)

    monkeypatch.setattr(httpx2, "AsyncClient", OfflineClient)
    monkeypatch.setenv("LUMIS_SYNTHETIC_KEY", "not-a-real-key")
    settings = ModelSettings(
        provider="anthropic",
        model="claude-sonnet-4-6",
        api_key_env="LUMIS_SYNTHETIC_KEY",
        cache_instructions="5m",
        cache_tool_definitions=True,
    )

    async def run():
        async with configured_investigator(settings, timeout=2) as agent:
            return await project.handle_incident(event, observations=facts, investigator=agent)

    report = asyncio.run(run())
    assert report.stop_reason == "agent_completed" and len(seen) == 1
    assert seen[0]["system"][-1]["cache_control"]["type"] == "ephemeral"
    assert seen[0]["tools"][-1]["cache_control"]["type"] == "ephemeral"
    assert report.metrics.cache_read_tokens == 80 and report.metrics.cache_write_tokens == 5


def test_bedrock_uses_pydantic_converse_wire_with_explicit_token_limit(tmp_path, monkeypatch):
    import boto3
    from botocore.config import Config
    from botocore.stub import Stubber
    from pydantic_ai.models.bedrock import BedrockConverseModel

    project, event, facts = estate(tmp_path)
    # Dummy credentials plus Stubber: no credential lookup, AWS request or paid model call.
    client = boto3.client(
        "bedrock-runtime",
        region_name="us-east-1",
        aws_access_key_id="synthetic-key",
        aws_secret_access_key="synthetic-secret",
        config=Config(retries={"total_max_attempts": 1}),
    )
    seen = []
    client.meta.events.register(
        "before-parameter-build.bedrock-runtime.Converse",
        lambda params, **kwargs: seen.append(params),
    )
    stubber = Stubber(client)
    stubber.add_response(
        "converse",
        {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"toolUse": {"toolUseId": "final", "name": "final_result", "input": {}}}
                    ],
                }
            },
            "stopReason": "tool_use",
            "usage": {"inputTokens": 100, "outputTokens": 10, "totalTokens": 110},
            "metrics": {"latencyMs": 1},
        },
    )

    class Session:
        def client(self, *args, **kwargs):
            return client

    monkeypatch.setattr(boto3, "Session", lambda **kwargs: Session())
    settings = ModelSettings(provider="bedrock", model="anthropic.claude-sonnet-4-5")

    async def run():
        async with configured_investigator(settings, timeout=2) as agent:
            assert isinstance(agent.agent.model, BedrockConverseModel)
            return await project.handle_incident(event, observations=facts, investigator=agent)

    with stubber:
        report = asyncio.run(run())
        stubber.assert_no_pending_responses()
    assert report.stop_reason == "agent_completed" and report.metrics.model_requests == 1
    assert seen[0]["modelId"] == settings.model
    assert seen[0]["inferenceConfig"]["maxTokens"] == project.config.budget.max_model_output_tokens
