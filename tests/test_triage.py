"""Tests for deterministic triage and diagnosis rules."""

from openaria.triage import diagnose_log


def test_key_error_is_classified_as_a_schema_change() -> None:
    """A missing expected column maps to the first supported failure type."""
    diagnosis = diagnose_log("ERROR Step: transform_prices\nERROR KeyError: 'Close'")

    assert diagnosis.triage.classification == "schema_change"
    assert diagnosis.triage.severity.value == "medium"
    assert diagnosis.confidence == 0.65
    assert diagnosis.evidence[0].id == "E1"
    assert "`Close`" in diagnosis.root_cause_hypothesis


def test_unmatched_log_remains_explicitly_unknown() -> None:
    """Unrecognized logs never receive an invented classification."""
    diagnosis = diagnose_log("ERROR process returned code 7")

    assert diagnosis.triage.classification == "unknown"
    assert diagnosis.confidence == 0.1
    assert "insufficient" in diagnosis.root_cause_hypothesis
