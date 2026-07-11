"""Deterministic Markdown report adapter."""

from collections.abc import Iterable

from openaria.domain import DiagnosisResult, IncidentInput


def render_markdown_report(incident: IncidentInput, diagnosis: DiagnosisResult) -> str:
    """Render a report that visibly separates evidence from uncertain reasoning."""
    pipeline_name = incident.pipeline_name or "not provided"
    evidence_lines = _bullets(f"[{item.id}] {item.detail}" for item in diagnosis.evidence)
    facts = _bullets(diagnosis.confirmed_facts)
    missing_evidence = _bullets(diagnosis.missing_evidence)
    next_steps = _numbered(diagnosis.recommended_next_steps)
    playbook = diagnosis.suggested_playbook or "No playbook suggested"

    return f"""# Incident Report

## Incident

- Source: {incident.source_tool}
- Pipeline: {pipeline_name}
- Environment: {incident.environment}
- Classification: {diagnosis.triage.classification}
- Severity: {diagnosis.triage.severity.value}
- Diagnosis method: {diagnosis.method.value}
- Human review required: {diagnosis.requires_human_review}

## Summary

{diagnosis.triage.summary}

## Confirmed Facts

{facts}

## Evidence

{evidence_lines}

## Likely Root Cause (Hypothesis)

{diagnosis.root_cause_hypothesis}

Confidence: {diagnosis.confidence:.0%}. This is a hypothesis, not a confirmed cause.

## Missing Evidence

{missing_evidence}

## Recommended Next Steps

{next_steps}

## Suggested Playbook

`{playbook}`

## Safety Boundary

This report recommends investigation steps only. OpenARIA has not executed a remediation action.
"""


def append_resolution(report_markdown: str, resolution: str | None) -> str:
    """Append a human-confirmed final resolution when one has been recorded."""
    if resolution is None:
        return report_markdown
    return f"{report_markdown.rstrip()}\n\n## Final Resolution\n\n{resolution}\n"


def _bullets(items: Iterable[str]) -> str:
    values = list(items)
    return "\n".join(f"- {value}" for value in values) if values else "- None recorded"


def _numbered(items: list[str]) -> str:
    if not items:
        return "1. No next step recorded"
    return "\n".join(f"{index}. {step}" for index, step in enumerate(items, start=1))
