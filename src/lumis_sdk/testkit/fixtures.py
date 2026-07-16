"""Stable synthetic fixtures for adapter and integration tests."""

from lumis_sdk.domain import EvidenceItem, IncidentInput


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
