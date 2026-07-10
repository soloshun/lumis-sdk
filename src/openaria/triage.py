"""Generic deterministic rule evaluation for configured OpenARIA projects."""

from openaria.config import DeterministicRule
from openaria.schemas import DiagnosisResult, EvidenceItem, Severity, TriageResult


def diagnose_text(log_text: str, rules: list[DeterministicRule]) -> DiagnosisResult:
    """Apply the first matching project-supplied rule to local text."""
    for rule in rules:
        if all(term.lower() in log_text.lower() for term in rule.all_contains):
            return _diagnosis_from_rule(log_text, rule)
    return _unknown_diagnosis(log_text)


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
        evidence=[EvidenceItem(id="E1", source="provided_log", detail=first_line, confidence=1.0)],
        missing_evidence=["a project-specific diagnosis rule", "additional incident context"],
        recommended_next_steps=["Add context or a project-specific deterministic rule."],
    )


def _matching_line(log_text: str, marker: str) -> str:
    """Return a log line that supplied a configured matching term."""
    for line in log_text.splitlines():
        if marker.lower() in line.lower():
            return line.strip()
    return marker
