"""Tests for versioned machine-readable diagnosis reports."""

from pathlib import Path

from lumis_sdk.adapters.deterministic import diagnose_text
from lumis_sdk.adapters.reports import (
    JsonReportWriter,
    diagnosis_report_json_schema,
    render_json_report,
)
from lumis_sdk.config import DeterministicRule
from lumis_sdk.domain import TruthState
from lumis_sdk.testkit import assert_json_report_round_trip, make_test_incident


def test_json_report_round_trips_without_losing_evidence_or_truth() -> None:
    """Downstream tooling receives a strict versioned report contract."""
    rule = DeterministicRule(
        id="fixture",
        name="fixture",
        all_contains=["TESTKIT_SIGNATURE"],
        classification="fixture_failure",
        severity="medium",
        summary="The fixture signature appeared.",
        root_cause_hypothesis="The fixture rule matched.",
        confidence=0.6,
    )
    incident = make_test_incident()
    diagnosis = diagnose_text("ERROR TESTKIT_SIGNATURE", [rule])

    value = render_json_report(
        incident,
        diagnosis,
        truth_state=TruthState.HUMAN_CONFIRMED,
        confirmed_resolution="Updated the synthetic fixture.",
    )
    document = assert_json_report_round_trip(value)

    assert document.api_version == "lumis.dev/v1alpha1"
    assert document.kind == "DiagnosisReport"
    assert document.truth_state is TruthState.HUMAN_CONFIRMED
    assert document.confirmed_resolution == "Updated the synthetic fixture."
    assert document.diagnosis.evidence[0].reference == "rule:fixture@1"


def test_json_report_schema_is_strict_and_uses_public_aliases() -> None:
    """The checked report schema is suitable for editors and generated clients."""
    schema = diagnosis_report_json_schema()

    assert schema["additionalProperties"] is False
    assert schema["properties"]["apiVersion"]["const"] == "lumis.dev/v1alpha1"
    assert "truthState" in schema["properties"]
    assert "confirmedResolution" in schema["properties"]


def test_json_report_writer_implements_the_public_destination_contract(tmp_path: Path) -> None:
    """The reference writer creates parent directories and returns the written path."""
    rule = DeterministicRule(
        id="fixture",
        name="fixture",
        all_contains=["TESTKIT_SIGNATURE"],
        classification="fixture_failure",
        severity="medium",
        summary="The fixture signature appeared.",
        root_cause_hypothesis="The fixture rule matched.",
        confidence=0.6,
    )
    destination = tmp_path / "nested/report.json"

    result = JsonReportWriter().write(
        incident=make_test_incident(),
        diagnosis=diagnose_text("TESTKIT_SIGNATURE", [rule]),
        destination=destination,
    )

    assert result == destination
    assert_json_report_round_trip(destination.read_text(encoding="utf-8"))
