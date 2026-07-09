"""Small, explainable triage rules for the first OpenARIA proof."""

import re

from openaria.schemas import DiagnosisResult, EvidenceItem, Severity, TriageResult

_KEY_ERROR_PATTERN = re.compile(r"KeyError:\s*['\"](?P<field>[^'\"]+)['\"]")


def diagnose_log(log_text: str) -> DiagnosisResult:
    """Diagnose a supplied log using deterministic, evidence-only rules.

    This deliberately handles one initial schema-mismatch signature and returns an
    explicit unknown result for every other input. It never calls a model or an
    external system.
    """
    key_error_match = _KEY_ERROR_PATTERN.search(log_text)
    if key_error_match:
        return _schema_mismatch_diagnosis(key_error_match.group("field"), log_text)

    return _unknown_diagnosis(log_text)


def _schema_mismatch_diagnosis(field_name: str, log_text: str) -> DiagnosisResult:
    error_line = _matching_line(log_text, "KeyError")
    step_line = _matching_line(log_text, "Step:")
    assert error_line is not None
    evidence = [
        EvidenceItem(
            id="E1",
            source="provided_log",
            detail=error_line,
            confidence=1.0,
        )
    ]
    facts = [f"The supplied log contains a KeyError for the expected field `{field_name}`."]

    if step_line:
        evidence.append(
            EvidenceItem(
                id="E2",
                source="provided_log",
                detail=step_line,
                confidence=1.0,
            )
        )
        facts.append("The supplied log identifies the step where the error surfaced.")

    return DiagnosisResult(
        triage=TriageResult(
            classification="schema_change",
            severity=Severity.MEDIUM,
            summary=(
                f"The pipeline stopped because a step expected a field named `{field_name}`, "
                "but the supplied log shows that field was unavailable."
            ),
            missing_context=[
                "current input schema",
                "last successful input schema",
                "recent code changes",
            ],
        ),
        confirmed_facts=facts,
        root_cause_hypothesis=(
            f"The upstream data format may have changed, or a normalization step may have "
            f"renamed or removed `{field_name}` before the failing step."
        ),
        confidence=0.65,
        evidence=evidence,
        missing_evidence=[
            "current input schema",
            "last successful input schema",
            "recent code changes",
        ],
        recommended_next_steps=[
            "Compare the current input schema with the last successful run.",
            "Confirm whether the upstream source changed its exported fields.",
            "Review the normalization mapping before changing pipeline code.",
            "Add a schema validation check before the failing transformation.",
        ],
        suggested_playbook="schema_mismatch_in_dataframe",
    )


def _unknown_diagnosis(log_text: str) -> DiagnosisResult:
    first_line = next(
        (line.strip() for line in log_text.splitlines() if line.strip()), "No log content"
    )
    return DiagnosisResult(
        triage=TriageResult(
            classification="unknown",
            severity=Severity.MEDIUM,
            summary="The supplied log did not match a deterministic diagnosis rule.",
            missing_context=["error type", "failing step", "recent pipeline context"],
        ),
        confirmed_facts=["A log was supplied for analysis."],
        root_cause_hypothesis=(
            "The available evidence is insufficient to identify a supported failure signature."
        ),
        confidence=0.1,
        evidence=[
            EvidenceItem(
                id="E1",
                source="provided_log",
                detail=first_line,
                confidence=1.0,
            )
        ],
        missing_evidence=["error type", "failing step", "recent pipeline context"],
        recommended_next_steps=[
            "Collect the full error message and stack trace.",
            "Identify the pipeline step that failed.",
            "Compare the failure with the last successful run.",
        ],
    )


def _matching_line(log_text: str, marker: str) -> str | None:
    """Return a trimmed log line containing a marker, if one exists."""
    for line in log_text.splitlines():
        if marker.lower() in line.lower():
            return line.strip()
    return None
