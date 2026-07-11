"""Explainable deterministic diagnosis adapter."""

from dataclasses import dataclass

from openaria.config import DeterministicRule
from openaria.domain import (
    DiagnosisMethod,
    DiagnosisResult,
    EvidenceItem,
    Severity,
    TriageResult,
)


@dataclass(frozen=True)
class RuleMatch:
    """Transparent metadata explaining one deterministic match."""

    rule_id: str
    rule_version: str
    priority: int
    matched_terms: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class DeterministicDiagnosis:
    """A diagnosis and its optional rule-match explanation."""

    diagnosis: DiagnosisResult
    match: RuleMatch | None


def diagnose_text(log_text: str, rules: list[DeterministicRule]) -> DiagnosisResult:
    """Apply the highest-priority first matching project rule to local text."""
    return diagnose_text_with_explanation(log_text, rules).diagnosis


def diagnose_text_with_explanation(
    log_text: str, rules: list[DeterministicRule]
) -> DeterministicDiagnosis:
    """Return a diagnosis plus stable rule and evidence references."""
    ordered_rules = sorted(enumerate(rules), key=lambda item: (-item[1].priority, item[0]))
    for _, rule in ordered_rules:
        if all(term.lower() in log_text.lower() for term in rule.all_contains):
            diagnosis = _diagnosis_from_rule(log_text, rule)
            evidence_ids = tuple(item.id for item in diagnosis.evidence)
            return DeterministicDiagnosis(
                diagnosis=diagnosis,
                match=RuleMatch(
                    rule_id=rule.stable_id,
                    rule_version=rule.version,
                    priority=rule.priority,
                    matched_terms=tuple(rule.all_contains),
                    evidence_ids=evidence_ids,
                ),
            )
    return DeterministicDiagnosis(diagnosis=_unknown_diagnosis(log_text), match=None)


def _diagnosis_from_rule(log_text: str, rule: DeterministicRule) -> DiagnosisResult:
    evidence_details = list(
        dict.fromkeys(_matching_line(log_text, term) for term in rule.all_contains)
    )
    evidence = [
        EvidenceItem(
            id=f"E{index}",
            source="provided_log",
            detail=detail,
            confidence=1.0,
            kind="log",
            reference=f"rule:{rule.stable_id}@{rule.version}",
            attributes={"rule_id": rule.stable_id, "rule_version": rule.version},
        )
        for index, detail in enumerate(evidence_details, start=1)
    ]
    return DiagnosisResult(
        triage=TriageResult(
            classification=rule.classification,
            severity=rule.severity,
            summary=rule.summary,
            missing_context=rule.missing_evidence,
        ),
        confirmed_facts=[f"The supplied log matched configured rule `{rule.name}`."],
        root_cause_hypothesis=rule.root_cause_hypothesis,
        confidence=rule.confidence,
        evidence=evidence,
        missing_evidence=rule.missing_evidence,
        recommended_next_steps=rule.recommended_next_steps,
        suggested_playbook=rule.suggested_playbook,
        method=DiagnosisMethod.DETERMINISTIC,
    )


def _unknown_diagnosis(log_text: str) -> DiagnosisResult:
    first_line = next(
        (line.strip() for line in log_text.splitlines() if line.strip()), "No log content"
    )
    return DiagnosisResult(
        triage=TriageResult(
            classification="unknown",
            severity=Severity.MEDIUM,
            summary="No configured deterministic rule matched the supplied incident text.",
            missing_context=["a project-specific diagnosis rule", "additional incident context"],
        ),
        confirmed_facts=["A log was supplied for analysis."],
        root_cause_hypothesis="The available evidence did not match a configured diagnosis rule.",
        confidence=0.1,
        evidence=[
            EvidenceItem(
                id="E1",
                source="provided_log",
                detail=first_line,
                confidence=1.0,
                kind="log",
            )
        ],
        missing_evidence=["a project-specific diagnosis rule", "additional incident context"],
        recommended_next_steps=["Add context or a project-specific deterministic rule."],
        method=DiagnosisMethod.ESCALATED,
    )


def _matching_line(log_text: str, marker: str) -> str:
    """Return a log line that supplied a configured matching term."""
    for line in log_text.splitlines():
        if marker.lower() in line.lower():
            return line.strip()
    return marker
