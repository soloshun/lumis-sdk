"""Standalone incident flow, real agent tool loop and evidence-authority boundaries."""

import asyncio
import json
import os
import sqlite3
from xml.etree import ElementTree

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from typer.testing import CliRunner

from lumis_sdk.cli.app import app
from lumis_sdk.connectors import SnapshotConnector
from lumis_sdk.core import Evidence, Incident, IncidentContext
from lumis_sdk.investigation.agent import PydanticInvestigator
from lumis_sdk.investigation.config import InvestigatorSettings
from lumis_sdk.investigation.contracts import (
    AgentOutput,
    HumanResolution,
    InspectRequest,
    ProbeSpec,
)
from lumis_sdk.investigation.tools import InvestigationTools, ToolBudgetExceeded
from lumis_sdk.runtime import IncidentStore, YamlProject
from lumis_sdk.runtime.project import OperationalProject
from lumis_sdk.runtime.scaffold import starter_documents


def estate(tmp_path, *, terminal=False, probe=False):
    documents = starter_documents()
    config = json.loads(documents["lumis.yaml"])
    hypothesis = config["checks"][0]["hypothesis"]
    if terminal:
        config["queries"].append(
            {
                "id": "ready",
                "provider": "snapshot",
                "entity_id": "service:demo",
                "key": "ready",
                "description": "Was readiness false?",
            }
        )
        hypothesis["evidence_needed"].append("ready")
        hypothesis["predictions"].append(
            {
                "entity_id": "service:demo",
                "key": "ready",
                "operator": "eq",
                "value": False,
            }
        )
        config["checks"][0].update(terminal=True, explains_entities=["service:demo"])
    config["rule_hypotheses"] = []
    if probe:
        config["queries"].append(
            {
                "id": "experiment",
                "provider": "probe",
                "entity_id": "service:demo",
                "key": "experiment",
                "description": "Synthetic reproduction, not production evidence",
            }
        )
        config["investigator"] = {
            "sandbox": {"enabled": True, "image": "python@sha256:" + "a" * 64}
        }
        config["budget"]["max_queries"] = 3
    (tmp_path / "lumis.yaml").write_text(json.dumps(config))
    (tmp_path / "incident.json").write_text(documents["incident.json"])
    facts = list(json.loads(documents["observations.json"]))
    if terminal:
        facts.append(facts[0] | {"id": "ready-fact", "query_id": "ready", "key": "ready"})
    (tmp_path / "observations.json").write_text(json.dumps(facts))
    return (
        YamlProject.from_file(tmp_path / "lumis.yaml"),
        Incident.model_validate_json(documents["incident.json"]),
        tuple(Evidence.model_validate(fact) for fact in facts),
    )


class RejectAgent:
    async def investigate(self, tools, findings):
        pytest.fail("terminal triage must not invoke the investigator")


def test_terminal_triage_skips_models_and_keeps_human_review(tmp_path):
    project, event, facts = estate(tmp_path, terminal=True)
    report = asyncio.run(
        project.handle_incident(
            event, observations=facts, investigator=RejectAgent(), use_agent=True
        )
    )
    assert report.route == "deterministic"
    assert report.conclusion == "supported_diagnosis"
    assert report.metrics.model_requests == report.metrics.tool_attempts == 0
    assert report.metrics.evidence_queries == 2
    assert report.truth_state == "unconfirmed_hypothesis" and report.requires_human_review


@pytest.mark.parametrize(
    "mode", ["nonterminal", "missing", "conflicting", "degraded", "competing", "guard"]
)
def test_insufficient_signature_escalates(tmp_path, mode):
    project, event, facts = estate(tmp_path, terminal=mode != "nonterminal")
    if mode == "missing":
        facts = facts[:1]
    if mode == "degraded":
        facts = tuple(fact.model_copy(update={"quality": "degraded"}) for fact in facts)
    if mode == "conflicting":
        facts = (*facts, facts[0].model_copy(update={"id": "contradiction", "value": True}))
    if mode == "competing":
        config = project.config.model_dump(mode="json")
        config["checks"].append(config["checks"][0] | {"id": "competing"})
        project = YamlProject(OperationalProject.model_validate(config), tmp_path)

    class Guard:
        def allows(self, rule, context):
            return False

    report = asyncio.run(
        project.handle_incident(
            event, observations=facts, guard=Guard() if mode == "guard" else None
        )
    )
    assert report.route == "human"
    assert report.conclusion == "requires_human_expert"
    assert report.metrics.model_requests == 0


def test_terminal_requires_multiple_observables_and_scope(tmp_path):
    project, _, _ = estate(tmp_path)
    data = project.config.model_dump(mode="json")
    data["checks"][0]["terminal"] = True
    with pytest.raises(ValueError, match="two distinct"):
        OperationalProject.model_validate(data)
    project, _, _ = estate(tmp_path, terminal=True)
    data = project.config.model_dump(mode="json")
    data["checks"][0]["explains_entities"] = []
    with pytest.raises(ValueError, match="explanation scope"):
        OperationalProject.model_validate(data)


def test_real_pydantic_agent_uses_dynamic_tools_and_structured_output(tmp_path):
    project, event, facts = estate(tmp_path)
    calls = []
    hypothesis = project.config.checks[0].hypothesis

    def model(messages, info):
        calls.append(messages)
        if len(calls) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "inspect", {"request": {"operation": "catalog"}}, tool_call_id="catalog"
                    )
                ]
            )
        if len(calls) == 2:
            assert "service:demo" in str(messages)
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "inspect",
                        {"request": {"operation": "graph", "target": "service:demo"}},
                        tool_call_id="graph",
                    )
                ]
            )
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {
                        "hypotheses": [hypothesis.model_dump(mode="json")],
                        "suggestions": [
                            {
                                "hypothesis_id": hypothesis.id,
                                "description": "Review service health.",
                                "evidence_ids": ["demo-health"],
                                "receipt_ids": ["tool-1"],
                            }
                        ],
                    },
                    tool_call_id="report",
                )
            ]
        )

    report = asyncio.run(
        project.handle_incident(
            event, observations=facts, investigator=PydanticInvestigator(FunctionModel(model))
        )
    )
    assert len(calls) == report.metrics.model_requests == 3
    assert report.metrics.tool_attempts == 2
    assert report.assessments[0].state == "supported"
    assert report.suggestions[0].requires_human_review
    assert report.route == "agent" and report.conclusion == "supported_diagnosis"


def test_request_limit_preserves_facts_and_never_accepts_invented_evidence(tmp_path):
    project, event, facts = estate(tmp_path)
    config = project.config.model_dump(mode="json")
    config["investigator"]["budget"]["request_limit"] = 1
    project = YamlProject(OperationalProject.model_validate(config), tmp_path)

    def looping(messages, info):
        return ModelResponse(
            parts=[ToolCallPart("inspect", {"request": {"operation": "catalog"}}, tool_call_id="c")]
        )

    report = asyncio.run(
        project.handle_incident(
            event, observations=facts, investigator=PydanticInvestigator(FunctionModel(looping))
        )
    )
    assert report.stop_reason == "investigator_rejected_or_unavailable"
    assert report.metrics.model_requests == 1 and report.context.evidence == facts

    class Inventor:
        async def investigate(self, tools, findings):
            return AgentOutput.model_validate(
                {
                    "hypotheses": [project.config.checks[0].hypothesis],
                    "suggestions": [
                        {
                            "hypothesis_id": project.config.checks[0].hypothesis.id,
                            "description": "Claim",
                            "evidence_ids": ["made-up"],
                        }
                    ],
                }
            )

    rejected = asyncio.run(
        project.handle_incident(event, observations=facts, investigator=Inventor())
    )
    assert not rejected.suggestions and rejected.conclusion == "insufficient_evidence"
    with pytest.raises(ValueError):
        AgentOutput.model_validate({"evidence": [{"value": True}]})


def broker(project, event, *, facts=(), runner=None, settings=None):
    return InvestigationTools(
        IncidentContext(incident=event, graph=project.config.graph, queries=project.config.queries),
        queries=project.config.queries,
        connectors={"snapshot": SnapshotConnector(facts)},
        settings=settings or project.config.investigator,
        budget=project.config.budget,
        base=project.base,
        runner=runner,
    )


def test_tool_attempts_query_cache_and_output_budgets(tmp_path):
    project, event, facts = estate(tmp_path)
    settings = InvestigatorSettings.model_validate(
        {
            "budget": {
                "tool_calls_limit": 3,
                "max_tool_characters": 100,
                "max_total_tool_characters": 100,
            }
        }
    )
    tools = broker(project, event, facts=facts, settings=settings)

    async def run():
        first = await tools.inspect(InspectRequest(operation="evidence", query_id="health"))
        cached = await tools.inspect(InspectRequest(operation="evidence", query_id="health"))
        denied = await tools.inspect(
            InspectRequest(operation="code.read", target="unknown", path=".env")
        )
        assert first.status == cached.status == "ok" and denied.status == "denied"
        assert len(tools.context.evidence) == 1 and len(tools.tried) == 1
        assert sum(len(receipt.output) for receipt in tools.receipts) <= 100
        with pytest.raises(ToolBudgetExceeded):
            await tools.inspect(InspectRequest(operation="catalog"))

    asyncio.run(run())


def test_failed_observations_remain_unknown_and_deadlines_preserve_facts(tmp_path):
    project, event, facts = estate(tmp_path)
    tools = broker(project, event)

    class Failing:
        async def collect(self, query, incident):
            raise RuntimeError("secret must not leak")

    tools.connectors["snapshot"] = Failing()
    receipt = asyncio.run(tools.collect("health"))
    assert receipt.status == "error" and not tools.context.evidence
    assert "secret" not in receipt.output
    data = project.config.model_dump(mode="json")
    data["budget"]["total_timeout_seconds"] = 0.02
    project = YamlProject(OperationalProject.model_validate(data), tmp_path)

    class Slow:
        async def investigate(self, tools, findings):
            await asyncio.sleep(1)
            return AgentOutput()

    report = asyncio.run(project.handle_incident(event, observations=facts, investigator=Slow()))
    assert report.stop_reason == "deadline_exceeded"
    assert report.context.evidence == facts and report.findings[0].status == "match"


def test_probe_is_bound_to_candidate_and_never_proves_a_diagnosis(tmp_path):
    project, event, _ = estate(tmp_path, probe=True)
    from lumis_sdk.core import Hypothesis

    candidate = Hypothesis.model_validate(
        {
            "id": "candidate",
            "statement": "Experiment reproduces symptom.",
            "causal_path": ["service:demo"],
            "evidence_needed": ["experiment"],
            "predictions": [
                {"entity_id": "service:demo", "key": "experiment", "operator": "eq", "value": True}
            ],
            "falsifiers": [
                {"entity_id": "service:demo", "key": "experiment", "operator": "eq", "value": False}
            ],
        }
    )

    class FakeRunner:
        async def run(self, spec, files):
            return True

    class Agent:
        async def investigate(self, tools, findings):
            spec = ProbeSpec(
                hypothesis_id="candidate",
                query_id="experiment",
                purpose="Reproduce",
                code='print("{"value":true}")',
            )
            assert (await tools.probe(spec)).status == "denied"
            tools.register(candidate)
            assert (await tools.probe(spec)).status == "ok"
            assert (await tools.probe(spec)).status == "denied"
            with pytest.raises(ValueError, match="new ID"):
                tools.register(candidate.model_copy(update={"statement": "Changed claim"}))
            return AgentOutput(hypotheses=(candidate,))

    report = asyncio.run(project.handle_incident(event, investigator=Agent(), runner=FakeRunner()))
    assert report.metrics.probes == 1
    assert report.assessments[0].state == "unresolved"
    assert report.context.evidence[0].quality == "degraded"
    assert report.conclusion == "insufficient_evidence"
    assert next(
        r for r in report.receipts if r.operation == "probe" and r.status == "ok"
    ).code_digest


def test_sqlite_resolution_is_append_only_and_separate(tmp_path):
    project, event, facts = estate(tmp_path, terminal=True)
    report = asyncio.run(project.handle_incident(event, observations=facts))
    store = IncidentStore(tmp_path / "audit.sqlite")
    store.save(report)
    assert store.get(event.id) == report and store.get("missing") is None
    resolution = HumanResolution(
        id="review-1",
        incident_id=event.id,
        reviewer="operator",
        recorded_at=event.ended_at,
        summary="Reviewed manually.",
        applied_change="None.",
        outcome="inconclusive",
    )
    store.record_resolution(resolution)
    assert store.get(event.id) == report and store.resolutions(event.id) == (resolution,)
    with pytest.raises(sqlite3.IntegrityError):
        store.save(report)
    with pytest.raises(sqlite3.IntegrityError):
        store.record_resolution(resolution)
    with pytest.raises(ValueError, match="existing"):
        store.record_resolution(
            resolution.model_copy(update={"id": "review-2", "incident_id": "missing"})
        )


def test_cli_incident_svg_console_and_manual_confirmation(tmp_path):
    project, _, _ = estate(tmp_path)
    runner = CliRunner()
    args = ["--project", str(tmp_path / "lumis.yaml")]
    result = runner.invoke(
        app,
        [
            "incident",
            *args,
            "--incident",
            str(tmp_path / "incident.json"),
            "--observations",
            str(tmp_path / "observations.json"),
            "--store",
            str(tmp_path / "audit.sqlite"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["route"] == "human"
    image = tmp_path / "graph.svg"
    result = runner.invoke(app, ["graph", *args, "--format", "svg", "--output", str(image)])
    assert result.exit_code == 0, result.output
    assert ElementTree.fromstring(image.read_text()).tag.endswith("svg")
    assert (
        runner.invoke(app, ["graph", *args, "--format", "svg", "--output", str(image)]).exit_code
        != 0
    )
    assert runner.invoke(app, ["console", *args], input="q\n").exit_code == 0
    record = tmp_path / "resolution.json"
    record.write_text("{}")
    assert (
        runner.invoke(
            app,
            [
                "record-resolution",
                "--store",
                str(tmp_path / "audit.sqlite"),
                "--resolution",
                str(record),
            ],
        ).exit_code
        != 0
    )


def test_svg_escapes_labels_and_empty_graph():
    from lumis_sdk.core import Entity, GraphSnapshot
    from lumis_sdk.graph.render import svg, terminal

    graph = GraphSnapshot(
        entities=(Entity(id="demo", kind="service", name="<script>alert(1)</script>"),)
    )
    assert "<script>" not in svg(graph)
    assert ElementTree.fromstring(svg(GraphSnapshot())) is not None
    assert "(no relationships" in terminal(graph)


@pytest.mark.skipif(
    not os.environ.get("LUMIS_TEST_SANDBOX_IMAGE"),
    reason="explicit digest-pinned Docker image required",
)
def test_real_agent_reads_code_registers_and_probes_in_docker(tmp_path):
    from lumis_sdk.sandbox.policy import SandboxPolicy
    from lumis_sdk.sandbox.runner import DockerProbeRunner

    project, event, facts = estate(tmp_path, probe=True)
    (tmp_path / "handler.py").write_text("def ready(value):\n    return bool(value)\n")
    config = project.config.model_dump(mode="json")
    config["investigator"]["repositories"] = [
        {"id": "source", "root": ".", "entity_ids": ["service:demo"], "files": ["handler.py"]}
    ]
    project = YamlProject(OperationalProject.model_validate(config), tmp_path)
    candidate = project.config.checks[0].hypothesis
    candidate = candidate.model_copy(
        update={
            "evidence_needed": ("health", "experiment"),
            "predictions": (
                *candidate.predictions,
                type(candidate.predictions[0])(
                    entity_id="service:demo", key="experiment", operator="eq", value=True
                ),
            ),
            "falsifiers": (
                *candidate.falsifiers,
                type(candidate.falsifiers[0])(
                    entity_id="service:demo", key="experiment", operator="eq", value=False
                ),
            ),
        }
    )
    probe_code = """import json, pathlib
text = pathlib.Path('snapshot/handler.py').read_text()
namespace = {}
exec(compile(text, 'snapshot/handler.py', 'exec'), namespace)
print(json.dumps({'value': namespace['ready'](False) is False}))
"""
    requests = [
        ("inspect", {"request": {"operation": "catalog"}}),
        (
            "inspect",
            {"request": {"operation": "code.read", "target": "source", "path": "handler.py"}},
        ),
        (
            "inspect",
            {
                "request": {
                    "operation": "hypothesis.register",
                    "hypothesis": candidate.model_dump(mode="json"),
                }
            },
        ),
        (
            "probe",
            {
                "spec": {
                    "hypothesis_id": candidate.id,
                    "query_id": "experiment",
                    "purpose": "Check copied readiness function",
                    "repository": "source",
                    "code": probe_code,
                }
            },
        ),
    ]
    count = 0

    def scripted(messages, info):
        nonlocal count
        count += 1
        if count <= len(requests):
            name, args = requests[count - 1]
            return ModelResponse(parts=[ToolCallPart(name, args, tool_call_id=f"t-{count}")])
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {"hypotheses": [candidate.model_dump(mode="json")]},
                    tool_call_id="report",
                )
            ]
        )

    runner = DockerProbeRunner(
        SandboxPolicy(enabled=True, image=os.environ["LUMIS_TEST_SANDBOX_IMAGE"])
    )
    report = asyncio.run(
        project.handle_incident(
            event,
            observations=facts,
            investigator=PydanticInvestigator(FunctionModel(scripted)),
            runner=runner,
        )
    )
    assert report.stop_reason == "agent_completed"
    assert report.metrics.model_requests == 5 and report.metrics.probes == 1
    assert report.assessments[0].state == "unresolved"
    assert report.conclusion == "insufficient_evidence"
    receipt = next(r for r in report.receipts if r.operation == "probe")
    assert receipt.status == "ok" and receipt.snapshot_digest and receipt.code_digest
    assert (tmp_path / "handler.py").read_text().startswith("def ready")
