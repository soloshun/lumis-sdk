"""Structured, explainable deterministic diagnosis evaluation."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from lumis_sdk.config import DiagnosisRuleDocument, RuleCondition
from lumis_sdk.domain import (
    DiagnosisMethod,
    DiagnosisResult,
    EvidenceItem,
    Severity,
    TriageResult,
)

MAX_EXPLANATION_VALUE_CHARS = 500


@dataclass(frozen=True)
class ConditionEvaluation:
    """The observed result of one rule condition."""

    path: str
    field: str
    operator: str
    expected: str | int | float | bool
    actual: Any
    passed: bool


@dataclass(frozen=True)
class StructuredRuleEvaluation:
    """A complete explanation for one structured rule candidate."""

    rule_id: str
    rule_version: str
    priority: int
    specificity: int
    matched: bool
    matched_conditions: tuple[ConditionEvaluation, ...]
    failed_conditions: tuple[ConditionEvaluation, ...]
    missing_evidence: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class StructuredDeterministicDiagnosis:
    """The selected diagnosis plus every evaluated candidate and ranking reason."""

    diagnosis: DiagnosisResult
    winner: StructuredRuleEvaluation | None
    candidates: tuple[StructuredRuleEvaluation, ...]
    selection_reason: str


def evaluate_diagnosis_rule(
    rule: DiagnosisRuleDocument,
    fields: Mapping[str, Any],
    evidence: Sequence[EvidenceItem] = (),
) -> StructuredRuleEvaluation:
    """Evaluate one validated rule against provider-neutral structured fields."""
    evaluations: list[ConditionEvaluation] = []
    for group_name, conditions in (
        ("all", rule.spec.match.all),
        ("any", rule.spec.match.any),
        ("not", rule.spec.match.not_),
    ):
        for index, condition in enumerate(conditions):
            raw = _evaluate_condition(
                condition,
                fields,
                path=f"spec.match.{group_name}[{index}]",
            )
            evaluations.append(
                raw
                if group_name != "not"
                else ConditionEvaluation(
                    path=raw.path,
                    field=raw.field,
                    operator=f"not {raw.operator}",
                    expected=raw.expected,
                    actual=raw.actual,
                    passed=not raw.passed,
                )
            )

    all_results = evaluations[: len(rule.spec.match.all)]
    any_start = len(all_results)
    any_end = any_start + len(rule.spec.match.any)
    any_results = evaluations[any_start:any_end]
    not_results = evaluations[any_end:]
    evidence_kinds = {item.kind for item in evidence}
    missing_evidence = tuple(
        kind for kind in rule.spec.evidence.required if kind not in evidence_kinds
    )
    matched = (
        all(item.passed for item in all_results)
        and (not any_results or any(item.passed for item in any_results))
        and all(item.passed for item in not_results)
        and not missing_evidence
    )
    references = tuple(
        dict.fromkeys(
            item.reference or item.id
            for item in evidence
            if not rule.spec.evidence.required or item.kind in rule.spec.evidence.required
        )
    )
    return StructuredRuleEvaluation(
        rule_id=rule.stable_id,
        rule_version=rule.metadata.version,
        priority=rule.spec.priority,
        specificity=rule.specificity,
        matched=matched,
        matched_conditions=tuple(item for item in evaluations if item.passed),
        failed_conditions=tuple(item for item in evaluations if not item.passed),
        missing_evidence=missing_evidence,
        evidence_references=references,
    )


def diagnose_structured(
    fields: Mapping[str, Any],
    rules: Sequence[DiagnosisRuleDocument],
    evidence: Sequence[EvidenceItem] = (),
) -> StructuredDeterministicDiagnosis:
    """Evaluate and rank structured rules by priority, specificity, then input order."""
    evaluated = [
        (index, rule, evaluate_diagnosis_rule(rule, fields, evidence))
        for index, rule in enumerate(rules)
    ]
    ranked = sorted(
        evaluated,
        key=lambda item: (
            not item[2].matched,
            -item[2].priority,
            -item[2].specificity,
            item[0],
        ),
    )
    candidates = tuple(item[2] for item in ranked)
    winner_entry = next((item for item in ranked if item[2].matched), None)
    if winner_entry is None:
        return StructuredDeterministicDiagnosis(
            diagnosis=_unknown_structured_diagnosis(fields, evidence),
            winner=None,
            candidates=candidates,
            selection_reason=(
                "No structured diagnosis rule satisfied all match and evidence requirements."
            ),
        )

    winner_index, winner_rule, winner = winner_entry
    outranked = [item[2] for item in evaluated if item[0] != winner_index and item[2].matched]
    reason = _selection_reason(winner, outranked)
    return StructuredDeterministicDiagnosis(
        diagnosis=_diagnosis_from_structured_rule(winner_rule, winner, evidence),
        winner=winner,
        candidates=candidates,
        selection_reason=reason,
    )


def _evaluate_condition(
    condition: RuleCondition,
    fields: Mapping[str, Any],
    *,
    path: str,
) -> ConditionEvaluation:
    actual = _resolve_field(fields, condition.field)
    operator, expected = _condition_operator(condition)
    passed = _compare(actual, operator, expected)
    return ConditionEvaluation(
        path=path,
        field=condition.field,
        operator=operator,
        expected=expected,
        actual=_bounded_actual(actual),
        passed=passed,
    )


def _condition_operator(condition: RuleCondition) -> tuple[str, str | int | float | bool]:
    for field_name, operator in (
        ("contains", "contains"),
        ("equals", "equals"),
        ("prefix", "prefix"),
        ("matches_regex", "matchesRegex"),
        ("greater_than", "greaterThan"),
        ("greater_than_or_equal", "greaterThanOrEqual"),
        ("less_than", "lessThan"),
        ("less_than_or_equal", "lessThanOrEqual"),
    ):
        value = getattr(condition, field_name)
        if value is not None:
            return operator, value
    raise AssertionError("validated rule condition has no operator")


def _compare(actual: Any, operator: str, expected: str | int | float | bool) -> bool:
    if operator == "contains":
        return isinstance(actual, str) and str(expected).casefold() in actual.casefold()
    if operator == "equals":
        return bool(actual == expected)
    if operator == "prefix":
        return isinstance(actual, str) and actual.startswith(str(expected))
    if operator == "matchesRegex":
        return isinstance(actual, str) and re.search(str(expected), actual) is not None
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return False
    numeric_actual = float(actual)
    numeric_expected = float(expected)
    if operator == "greaterThan":
        return numeric_actual > numeric_expected
    if operator == "greaterThanOrEqual":
        return numeric_actual >= numeric_expected
    if operator == "lessThan":
        return numeric_actual < numeric_expected
    if operator == "lessThanOrEqual":
        return numeric_actual <= numeric_expected
    return False


def _resolve_field(fields: Mapping[str, Any], path: str) -> Any:
    if path in fields:
        return fields[path]
    current: Any = fields
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _bounded_actual(actual: Any) -> Any:
    """Keep explanations useful without echoing an unbounded telemetry value."""
    if not isinstance(actual, str) or len(actual) <= MAX_EXPLANATION_VALUE_CHARS:
        return actual
    omitted = len(actual) - MAX_EXPLANATION_VALUE_CHARS
    return f"{actual[:MAX_EXPLANATION_VALUE_CHARS]}... [{omitted} characters omitted]"


def _diagnosis_from_structured_rule(
    rule: DiagnosisRuleDocument,
    winner: StructuredRuleEvaluation,
    evidence: Sequence[EvidenceItem],
) -> DiagnosisResult:
    diagnosis = rule.spec.diagnosis
    return DiagnosisResult(
        triage=TriageResult(
            classification=diagnosis.classification,
            severity=diagnosis.severity,
            summary=diagnosis.summary,
            missing_context=diagnosis.missing_evidence,
        ),
        confirmed_facts=diagnosis.confirmed_facts,
        root_cause_hypothesis=diagnosis.hypothesis,
        confidence=diagnosis.confidence,
        evidence=list(evidence),
        missing_evidence=diagnosis.missing_evidence,
        recommended_next_steps=rule.spec.recommended_next_steps,
        suggested_playbook=rule.spec.suggested_playbook,
        method=DiagnosisMethod.DETERMINISTIC,
    )


def _unknown_structured_diagnosis(
    fields: Mapping[str, Any], evidence: Sequence[EvidenceItem]
) -> DiagnosisResult:
    return DiagnosisResult(
        triage=TriageResult(
            classification="unknown",
            severity=Severity.MEDIUM,
            summary="No structured deterministic rule matched the supplied incident fields.",
            missing_context=["a matching structured diagnosis rule", "additional evidence"],
        ),
        confirmed_facts=["Structured incident fields were supplied for deterministic evaluation."],
        root_cause_hypothesis="The available fields did not satisfy a configured diagnosis rule.",
        confidence=0.1,
        evidence=list(evidence),
        missing_evidence=["a matching structured diagnosis rule", "additional evidence"],
        recommended_next_steps=[
            "Inspect failed condition explanations and collect missing evidence."
        ],
        method=DiagnosisMethod.ESCALATED,
    )


def _selection_reason(
    winner: StructuredRuleEvaluation,
    other_matches: Sequence[StructuredRuleEvaluation],
) -> str:
    if not other_matches:
        return (
            f"{winner.rule_id}@{winner.rule_version} was the only rule that satisfied "
            "all condition and evidence requirements."
        )
    runner_up = sorted(
        other_matches,
        key=lambda item: (-item.priority, -item.specificity),
    )[0]
    if winner.priority != runner_up.priority:
        comparison = f"priority {winner.priority} outranked {runner_up.priority}"
    elif winner.specificity != runner_up.specificity:
        comparison = f"specificity {winner.specificity} outranked {runner_up.specificity}"
    else:
        comparison = "configured input order broke an equal priority and specificity tie"
    return (
        f"{winner.rule_id}@{winner.rule_version} won because {comparison}; "
        f"the next matching candidate was {runner_up.rule_id}@{runner_up.rule_version}."
    )
