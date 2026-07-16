"""Stable synthetic fixtures for adapter and integration tests."""

from datetime import UTC, datetime
from uuid import UUID

from lumis_sdk.domain import (
    ConfirmedResolution,
    DiagnosisMethod,
    DiagnosisResult,
    EvidenceItem,
    IncidentInput,
    Severity,
    TriageResult,
    TruthState,
)
from lumis_sdk.ports import IncidentEpisode

TEST_INCIDENT_ID = "11111111-1111-4111-8111-111111111111"


def make_test_incident() -> IncidentInput:
    """Return a provider-neutral synthetic incident."""
    return IncidentInput(
        source_tool="testkit",
        pipeline_name="synthetic-pipeline",
        environment="test",
        raw_payload={"log": "ERROR TESTKIT_SIGNATURE"},
    )


def make_test_evidence(
    *,
    evidence_id: str = "test-evidence-1",
    kind: str = "log_window",
) -> EvidenceItem:
    """Return one synthetic evidence item with a stable public reference."""
    return EvidenceItem(
        id=evidence_id,
        source="testkit",
        kind=kind,
        detail="ERROR TESTKIT_SIGNATURE",
        confidence=1.0,
        reference=f"testkit://evidence/{evidence_id}",
    )


def make_test_collection_fields() -> dict[str, object]:
    """Return deterministic list-valued fields for quantified rule contract tests."""
    return {
        "components": {
            "references": [
                "dbt.model.orders",
                "dbt.source.raw_orders",
                "airflow.dag.daily_orders",
            ]
        },
        "durations": [15, 30, 120],
    }


def make_test_episode(*, incident_id: str = TEST_INCIDENT_ID) -> IncidentEpisode:
    """Return one stable, unconfirmed operational-memory episode."""
    return IncidentEpisode(
        incident_id=incident_id,
        incident=make_test_incident(),
        diagnosis=DiagnosisResult(
            triage=TriageResult(
                classification="testkit_failure",
                severity=Severity.MEDIUM,
                summary="A synthetic testkit incident occurred.",
            ),
            confirmed_facts=["TESTKIT_SIGNATURE was observed."],
            root_cause_hypothesis="The synthetic dependency was unavailable.",
            confidence=0.8,
            method=DiagnosisMethod.DETERMINISTIC,
        ),
        truth_state=TruthState.UNCONFIRMED_HYPOTHESIS,
    )


def make_test_resolution(
    *,
    incident_id: str = TEST_INCIDENT_ID,
) -> ConfirmedResolution:
    """Return a stable human-confirmed resolution for a test episode."""
    return ConfirmedResolution(
        incident_id=UUID(incident_id),
        confirmed_root_cause="The synthetic dependency was unavailable.",
        action_taken="Restored the synthetic dependency.",
        outcome="The fixture pipeline recovered.",
        verified=True,
        confirmed_by="testkit-user",
        confirmed_at=datetime(2026, 1, 1, tzinfo=UTC),
        reusable_notes=["Check the synthetic dependency health first."],
        truth_state=TruthState.HUMAN_CONFIRMED,
    )
