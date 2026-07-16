"""Contract tests for portable structured deterministic diagnosis rules."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from lumis_sdk.adapters.deterministic import diagnose_structured, evaluate_diagnosis_rule
from lumis_sdk.config import DiagnosisRuleDocument, load_diagnosis_rule
from lumis_sdk.domain import EvidenceItem


def _rule(
    name: str = "schema-change",
    *,
    priority: int = 100,
    extra_all: bool = False,
) -> DiagnosisRuleDocument:
    all_conditions = [
        {"field": "log.text", "contains": "KeyError"},
        {"field": "schema.diff.removed_count", "greaterThan": 0},
    ]
    if extra_all:
        all_conditions.append({"field": "component.type", "equals": "transformation"})
    return DiagnosisRuleDocument.model_validate(
        {
            "apiVersion": "lumis.dev/v1alpha1",
            "kind": "DiagnosisRule",
            "metadata": {"name": name, "version": "2"},
            "spec": {
                "priority": priority,
                "match": {
                    "all": all_conditions,
                    "any": [
                        {"field": "labels.team", "equals": "data-platform"},
                        {"field": "environment", "equals": "production"},
                    ],
                    "not": [{"field": "status", "equals": "resolved"}],
                },
                "diagnosis": {
                    "classification": "schema_change",
                    "severity": "high",
                    "summary": "A required field was removed.",
                    "hypothesis": "The upstream schema changed.",
                    "confidence": 0.8,
                    "confirmedFacts": ["The current schema has removed fields."],
                    "missingEvidence": ["previous successful schema", "upstream change record"],
                },
                "evidence": {"required": ["schema_diff"]},
                "recommendedNextSteps": ["Compare the current and previous schemas."],
                "suggestedPlaybook": "investigate-schema-contract",
            },
        }
    )


def _fields() -> dict[str, object]:
    return {
        "log": {"text": "ERROR KeyError: customer_id"},
        "schema": {"diff": {"removed_count": 1}},
        "component": {"type": "transformation"},
        "labels": {"team": "data-platform"},
        "environment": "staging",
        "status": "open",
    }


def _evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            id="schema-1",
            source="schema-registry",
            kind="schema_diff",
            detail="customer_id was removed",
            confidence=1.0,
            reference="schema://orders/current-vs-previous",
        )
    ]


def test_compound_rule_explains_conditions_required_evidence_and_references() -> None:
    rule = _rule()

    result = evaluate_diagnosis_rule(rule, _fields(), _evidence())

    assert result.matched is True
    assert result.rule_id == "schema-change"
    assert result.rule_version == "2"
    assert len(result.matched_conditions) == 4
    assert len(result.failed_conditions) == 1
    assert result.missing_evidence == ()
    assert result.evidence_references == ("schema://orders/current-vs-previous",)


def test_missing_evidence_and_failed_any_condition_prevent_match() -> None:
    fields = _fields()
    fields["labels"] = {"team": "payments"}

    result = evaluate_diagnosis_rule(_rule(), fields)

    assert result.matched is False
    assert result.missing_evidence == ("schema_diff",)
    assert any(item.path.startswith("spec.match.any") for item in result.failed_conditions)


def test_priority_then_specificity_then_input_order_selects_winner() -> None:
    broad = _rule("broad")
    specific = _rule("specific", extra_all=True)
    lower_priority = _rule("lower-priority", priority=50, extra_all=True)

    result = diagnose_structured(_fields(), [broad, lower_priority, specific], _evidence())

    assert result.winner is not None
    assert result.winner.rule_id == "specific"
    assert result.diagnosis.triage.classification == "schema_change"
    assert result.diagnosis.missing_evidence == [
        "previous successful schema",
        "upstream change record",
    ]
    assert result.diagnosis.triage.missing_context == result.diagnosis.missing_evidence
    assert "specificity" in result.selection_reason
    assert result.candidates[0].rule_id == "specific"


def test_explanations_do_not_echo_unbounded_telemetry_values() -> None:
    rule = DiagnosisRuleDocument.model_validate(
        {
            "apiVersion": "lumis.dev/v1alpha1",
            "kind": "DiagnosisRule",
            "metadata": {"name": "large-log"},
            "spec": {
                "match": {"all": [{"field": "log.text", "contains": "SIGNATURE"}]},
                "diagnosis": {
                    "classification": "known",
                    "summary": "A bounded explanation is required.",
                    "hypothesis": "The signature appeared.",
                    "confidence": 0.5,
                },
            },
        }
    )

    result = evaluate_diagnosis_rule(rule, {"log": {"text": "SIGNATURE" + "x" * 2_000}})

    actual = result.matched_conditions[0].actual
    assert isinstance(actual, str)
    assert len(actual) < 600
    assert "characters omitted" in actual


def test_single_document_loader_is_strict_and_bounded(tmp_path: Path) -> None:
    path = tmp_path / "rule.yml"
    path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRule
metadata:
  name: timeout
spec:
  match:
    all:
      - field: duration.seconds
        greaterThan: 300
  diagnosis:
    classification: orchestration_failure
    summary: A task exceeded its expected duration.
    hypothesis: The task may be stuck.
    confidence: 0.7
""",
        encoding="utf-8",
    )

    document = load_diagnosis_rule(path)

    assert document.stable_id == "timeout"
    assert document.metadata.version == "1"
    with pytest.raises(ValidationError, match="exactly one"):
        DiagnosisRuleDocument.model_validate(
            {
                "apiVersion": "lumis.dev/v1alpha1",
                "kind": "DiagnosisRule",
                "metadata": {"name": "invalid"},
                "spec": {
                    "match": {
                        "all": [
                            {
                                "field": "log.text",
                                "contains": "error",
                                "equals": "error",
                            }
                        ]
                    },
                    "diagnosis": {
                        "classification": "unknown",
                        "summary": "Invalid.",
                        "hypothesis": "Invalid.",
                        "confidence": 0.1,
                    },
                },
            }
        )

    with pytest.raises(ValidationError, match="matchesRegex is invalid"):
        DiagnosisRuleDocument.model_validate(
            {
                "apiVersion": "lumis.dev/v1alpha1",
                "kind": "DiagnosisRule",
                "metadata": {"name": "invalid-regex"},
                "spec": {
                    "match": {"all": [{"field": "log.text", "matchesRegex": "["}]},
                    "diagnosis": {
                        "classification": "unknown",
                        "summary": "Invalid.",
                        "hypothesis": "Invalid.",
                        "confidence": 0.1,
                    },
                },
            }
        )


def test_required_and_outstanding_evidence_cannot_be_ambiguous() -> None:
    """A kind cannot gate matching and remain outstanding after that same rule matches."""
    payload = _rule().model_dump(by_alias=True)
    diagnosis = payload["spec"]["diagnosis"]
    assert isinstance(diagnosis, dict)
    diagnosis["missingEvidence"] = ["schema_diff"]

    with pytest.raises(ValidationError, match="must be distinct"):
        DiagnosisRuleDocument.model_validate(payload)
