"""Standalone kernel invariants using only synthetic operational contracts."""

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError
from typer.testing import CliRunner

from lumis_sdk.cli.app import app
from lumis_sdk.connectors import SnapshotConnector, merge_topology
from lumis_sdk.core import (
    Check,
    Entity,
    Evidence,
    GraphSnapshot,
    Hypothesis,
    Incident,
    IncidentContext,
    Investigation,
    InvestigationBudget,
    Relationship,
)
from lumis_sdk.core.contracts import validate_hypothesis
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.reasoning import MemoryHypothesisSource, ModelHypothesisSource, RuleSource, assess
from lumis_sdk.runtime import InvestigationRuntime, InvestigationStore
from lumis_sdk.runtime.project import load_project

EXAMPLE = Path(__file__).parent / "fixtures/operational"


def fixture():
    project = load_project(EXAMPLE / "lumis.yaml")
    incident = Incident.model_validate_json((EXAMPLE / "incident.json").read_text())
    facts = TypeAdapter(tuple[Evidence, ...]).validate_json(
        (EXAMPLE / "observations.json").read_text()
    )
    return project, incident, facts


def run(*, facts=None, budget=None, sources=None, generation_only=False):
    project, incident, default_facts = fixture()
    runtime = InvestigationRuntime(
        graph=OperationalGraph(project.graph),
        queries=project.queries,
        sources=sources or [RuleSource(project.rule_hypotheses)],
        connectors={"snapshot": SnapshotConnector(default_facts if facts is None else facts)},
        budget=budget or project.budget,
    )
    return asyncio.run(
        runtime.investigate(
            incident,
            initial_query_ids=project.initial_query_ids,
            generation_only=generation_only,
        )
    )


def test_hypotheses_require_falsifiers_and_graph_membership():
    project, incident, _ = fixture()
    hypothesis = project.rule_hypotheses[0]
    with pytest.raises(ValidationError):
        Hypothesis.model_validate(hypothesis.model_dump() | {"falsifiers": []})
    context = IncidentContext(incident=incident, graph=project.graph, queries=project.queries)
    with pytest.raises(ValueError, match="outside incident graph"):
        validate_hypothesis(hypothesis.model_copy(update={"causal_path": ("invented",)}), context)
    with pytest.raises(ValueError, match="unregistered"):
        validate_hypothesis(hypothesis.model_copy(update={"evidence_needed": ("shell",)}), context)


def test_competing_candidates_are_tested_without_confirmation():
    result = run()
    assert result.outcome == "supported"
    assert [item.state for item in result.assessments] == [
        "supported",
        "contradicted",
        "contradicted",
    ]
    assert result.truth_state == "unconfirmed_hypothesis"
    assert len([step for step in result.trace if step.kind == "query"]) == 4
    assert result.assessments[0].supporting_evidence_ids
    assert not hasattr(result, "action")
    assert Investigation.model_validate_json(result.model_dump_json()) == result


def test_all_sources_share_validation_and_evaluation():
    project, _, _ = fixture()

    class Stub:
        async def generate(self, context):
            return project.rule_hypotheses

    deterministic = run(sources=[RuleSource(project.rule_hypotheses)])
    model = run(sources=[ModelHypothesisSource(Stub())])
    memory = run(sources=[MemoryHypothesisSource(project.rule_hypotheses)])
    assert [item.state for item in deterministic.assessments] == [
        item.state for item in model.assessments
    ]
    assert [item.state for item in memory.assessments] == [item.state for item in model.assessments]
    combined = run(
        sources=[
            RuleSource(project.rule_hypotheses),
            MemoryHypothesisSource(project.rule_hypotheses),
        ]
    )
    assert len(combined.assessments) == 3
    assert combined.assessments[0].sources == ("rules", "memory")


def test_withheld_evidence_abstains_and_roundtrips_as_precedent(tmp_path):
    result = run(facts=())
    assert result.outcome == "abstained"
    assert result.stop_reason == "budget_exhausted"
    assert any(item.missing_checks for item in result.assessments)
    store = InvestigationStore(tmp_path / "memory.sqlite")
    store.save(result)
    assert store.get(result.context.incident.id) == result
    assert store.get("missing") is None
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        store.save(result)


def test_generation_only_returns_three_candidates_without_conclusions():
    result = run(generation_only=True)
    assert result.outcome == "hypotheses_ready"
    assert len(result.assessments) == 3
    assert result.stop_reason == "generation_only"


def test_zero_query_budget_is_enforced_including_initial_collection():
    result = run(budget=InvestigationBudget(max_queries=0))
    assert result.outcome == "abstained"
    assert not result.context.evidence
    assert not [step for step in result.trace if step.kind == "query"]


def test_no_discriminating_query_remains_a_normal_terminal_state():
    # All candidates are falsified by healthy database + no pressure + low reads.
    _, _, facts = fixture()
    changed = tuple(
        item.model_copy(update={"value": 1.0}) if item.key == "read_multiplier" else item
        for item in facts
    )
    result = run(facts=changed, budget=InvestigationBudget(max_queries=10))
    assert result.outcome == "abstained"
    assert result.stop_reason == "no_discriminating_query"
    assert all(item.state == "contradicted" for item in result.assessments)


def test_malformed_source_cannot_forge_evidence_or_graph():
    project, _, _ = fixture()
    invalid = project.rule_hypotheses[0].model_copy(update={"causal_path": ("unknown",)})
    result = run(sources=[RuleSource((invalid,))])
    assert result.stop_reason == "no_candidates"
    assert result.trace[1].status == "rejected"


def test_stale_or_misrouted_observations_cannot_support_candidates():
    _, _, facts = fixture()
    stale = tuple(
        item.model_copy(update={"observed_at": item.observed_at.replace(year=2025)})
        for item in facts
    )
    result = run(facts=stale)
    assert not result.context.evidence
    assert result.outcome == "abstained"
    assert all(step.status == "error" for step in result.trace if step.kind == "query")


def test_conflicting_and_degraded_observations_remain_unknown():
    project, incident, facts = fixture()
    conflict = facts[0].model_copy(update={"id": "conflicting", "value": False})
    context = IncidentContext(
        incident=incident,
        graph=project.graph,
        queries=project.queries,
        evidence=(facts[0], conflict),
    )
    assert assess(project.rule_hypotheses[1], context, ("rules",)).state == "unresolved"
    degraded = facts[0].model_copy(update={"quality": "degraded"})
    context = context.model_copy(update={"evidence": (degraded,)})
    assert assess(project.rule_hypotheses[1], context, ("rules",)).state == "unresolved"


def test_graph_cycles_bounds_and_direction():
    graph = OperationalGraph(
        GraphSnapshot(
            entities=tuple(
                Entity(id=key, name=key, kind="service") for key in ("a", "b", "c", "d")
            ),
            relationships=(
                Relationship(source="a", target="b", kind="feeds"),
                Relationship(source="b", target="c", kind="feeds"),
                Relationship(source="c", target="a", kind="feeds"),
            ),
        )
    )
    assert graph.downstream_of("a", hops=1) == ("b",)
    assert graph.upstream_of("a", hops=1) == ("c",)
    assert len(graph.scope(("a",), hops=8).entities) == 3
    with pytest.raises(ValueError, match="budget"):
        graph.scope(("a",), max_entities=2)
    with pytest.raises(ValueError, match="unknown"):
        graph.scope(("absent",))
    assert graph.scope(("a",), hops=0).entities[0].id == "a"


def test_topology_merge_does_not_overwrite_declared_context():
    original = GraphSnapshot(
        entities=(Entity(id="x", kind="service", name="X", attributes={"owner": "team"}),)
    )
    discovered = GraphSnapshot(
        entities=(Entity(id="x", kind="service", name="X", provenance=("otel",)),)
    )
    assert merge_topology(original, discovered).entities[0].attributes == {"owner": "team"}
    conflict = GraphSnapshot(
        entities=(Entity(id="x", kind="service", name="X", attributes={"owner": "other"}),)
    )
    with pytest.raises(ValueError, match="conflicting"):
        merge_topology(original, conflict)


def test_repeated_runs_have_identical_serialization_and_versions():
    serialized = [run().model_dump_json() for _ in range(5)]
    assert len(set(serialized)) == 1
    assert json.loads(serialized[0])["sdk_version"]


def test_redaction_preserves_timestamps_and_removes_credentials():
    project, incident, facts = fixture()
    incident = incident.model_copy(update={"symptoms": ("password=example-private-value",)})
    query = project.queries[0].model_copy(update={"parameters": {"credential": "private-value"}})
    result = asyncio.run(
        InvestigationRuntime(
            graph=OperationalGraph(project.graph),
            sources=[RuleSource(project.rule_hypotheses)],
            queries=(query, *project.queries[1:]),
            connectors={"snapshot": SnapshotConnector(facts)},
        ).investigate(incident)
    )
    assert "example-private-value" not in result.model_dump_json()
    assert "private-value" not in result.model_dump_json()
    assert result.context.incident.started_at == incident.started_at


def test_ordered_comparison_rejects_boolean_and_nan():
    with pytest.raises(ValidationError):
        Check(entity_id="a", key="metric", operator="gt", value=True)
    with pytest.raises(ValidationError):
        Check(entity_id="a", key="metric", operator="gt", value=float("nan"))


def test_cli_offline_outputs_structured_result():
    result = CliRunner().invoke(
        app,
        [
            "investigate",
            "--project",
            str(EXAMPLE / "lumis.yaml"),
            "--incident",
            str(EXAMPLE / "incident.json"),
            "--observations",
            str(EXAMPLE / "observations.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["outcome"] == "supported"


def test_project_rejects_aliases_and_unknown_fields(tmp_path):
    from lumis_sdk.runtime.project import load_project

    path = tmp_path / "project.yaml"
    path.write_text("name: &name project\nunknown: *name\n")
    with pytest.raises(ValueError, match="aliases"):
        load_project(path)
    project, _, _ = fixture()
    with pytest.raises(ValidationError):
        type(project).model_validate(project.model_dump() | {"execute": True})


def test_duplicate_graph_and_query_ids_are_rejected():
    project, incident, _ = fixture()
    with pytest.raises(ValidationError, match="duplicate"):
        GraphSnapshot(entities=(project.graph.entities[0], project.graph.entities[0]))
    with pytest.raises(ValidationError, match="duplicate"):
        IncidentContext(
            incident=incident, graph=project.graph, queries=(project.queries[0], project.queries[0])
        )


def test_one_invalid_source_candidate_is_traced_not_fatal():
    project, _, _ = fixture()
    valid = project.rule_hypotheses
    forged = valid[0].model_copy(update={"id": "forged", "causal_path": ("forged-entity",)})
    result = run(sources=[RuleSource((forged, *valid))], generation_only=True)
    assert len(result.assessments) == len(valid)
    rejected = [step for step in result.trace if step.status == "rejected"]
    assert [step.reason[:12] for step in rejected] == ["candidate 1:"]
