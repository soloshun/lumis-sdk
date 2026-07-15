"""Tests for deterministic triage and diagnosis rules."""

from lumis_sdk.adapters.deterministic import diagnose_text
from lumis_sdk.config import DeterministicRule


def test_configured_rule_is_applied_to_matching_text() -> None:
    """A consuming project controls its own deterministic classification."""
    rule = DeterministicRule(
        id="configured-rule",
        name="configured-rule",
        all_contains=["INCIDENT_SIGNATURE"],
        classification="configured_failure",
        severity="medium",
        summary="The configured signature appeared.",
        root_cause_hypothesis="The configured rule matched the supplied text.",
        confidence=0.6,
    )
    diagnosis = diagnose_text("ERROR INCIDENT_SIGNATURE", [rule])

    assert diagnosis.triage.classification == "configured_failure"
    assert diagnosis.triage.severity.value == "medium"
    assert diagnosis.confidence == 0.6
    assert diagnosis.evidence[0].id == "E1"
    assert "configured rule" in diagnosis.root_cause_hypothesis


def test_unmatched_log_remains_explicitly_unknown() -> None:
    """Unrecognized logs never receive an invented classification."""
    diagnosis = diagnose_text("ERROR process returned code 7", [])

    assert diagnosis.triage.classification == "unknown"
    assert diagnosis.confidence == 0.1
    assert "configured diagnosis rule" in diagnosis.root_cause_hypothesis
