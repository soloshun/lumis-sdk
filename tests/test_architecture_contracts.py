"""Contract tests for canonical application, adapter, and truth-state boundaries."""

import asyncio
from pathlib import Path

from lumis_sdk.adapters.deterministic import diagnose_text_with_explanation
from lumis_sdk.adapters.sqlite import SQLiteIncidentStore
from lumis_sdk.application import DiagnosisService
from lumis_sdk.config import DeterministicRule
from lumis_sdk.domain import (
    DiagnosisMethod,
    DiagnosisResult,
    IncidentInput,
    Severity,
    TriageResult,
    TruthState,
)
from lumis_sdk.ports import ModelUsePolicy
from lumis_sdk.testkit import FakeModelGateway


def _rule(name: str, *, priority: int, classification: str) -> DeterministicRule:
    return DeterministicRule(
        id=name,
        name=name,
        version="1",
        priority=priority,
        all_contains=["SIGNATURE"],
        classification=classification,
        severity="medium",
        summary=f"{name} matched.",
        root_cause_hypothesis=f"{name} may explain the incident.",
        confidence=0.6,
    )


def test_priority_is_explainable_and_equal_priority_order_is_stable() -> None:
    """Higher priority wins, while equal-priority rules retain configured order."""
    explanation = diagnose_text_with_explanation(
        "SIGNATURE",
        [
            _rule("lower", priority=10, classification="lower"),
            _rule("higher", priority=100, classification="higher"),
        ],
    )
    equal = diagnose_text_with_explanation(
        "SIGNATURE",
        [
            _rule("first", priority=0, classification="first"),
            _rule("second", priority=0, classification="second"),
        ],
    )

    assert explanation.diagnosis.triage.classification == "higher"
    assert explanation.match is not None
    assert explanation.match.rule_id == "higher"
    assert equal.diagnosis.triage.classification == "first"


def test_model_service_is_explicit_and_uses_fake_gateway_only_for_unknown() -> None:
    """The application service remains deterministic-first and network-free in CI."""
    model_diagnosis = DiagnosisResult(
        triage=TriageResult(
            classification="model_assisted_fixture",
            severity=Severity.MEDIUM,
            summary="The fake model returned a structured diagnosis.",
        ),
        root_cause_hypothesis="A fixture-only hypothesis.",
        confidence=0.5,
        method=DiagnosisMethod.MODEL_ASSISTED,
    )
    gateway = FakeModelGateway(model_diagnosis)
    service = DiagnosisService(
        rules=[],
        model_gateway=gateway,
        model_policy=ModelUsePolicy(enabled=True),
    )
    incident = IncidentInput(source_tool="fixture", raw_payload={"log": "UNKNOWN"})

    result = asyncio.run(service.diagnose(incident))

    assert result.triage.classification == "model_assisted_fixture"
    assert gateway.calls == 1


def test_sqlite_memory_exposes_truth_state(tmp_path: Path) -> None:
    """Existing resolution storage maps to visible truth state without altering the table."""
    store = SQLiteIncidentStore(tmp_path / "incidents.db")
    incident = IncidentInput(source_tool="fixture", raw_payload={"log": "SIGNATURE"})
    diagnosis = diagnose_text_with_explanation(
        "SIGNATURE", [_rule("fixture", priority=0, classification="fixture")]
    ).diagnosis
    stored = store.save(incident, diagnosis, "report", Path("report.md"))

    assert stored.truth_state is TruthState.UNCONFIRMED_HYPOTHESIS
    resolved = store.set_resolution(stored.id, "Human confirmed the fixture resolution.")
    assert resolved.truth_state is TruthState.HUMAN_CONFIRMED
