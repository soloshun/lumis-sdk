"""Render diagnosis results as human-readable Markdown reports."""

from openaria.schemas import DiagnosisResult, IncidentInput


def render_markdown_report(incident: IncidentInput, diagnosis: DiagnosisResult) -> str:
    """Render a report that visibly separates evidence from uncertain reasoning."""
    pipeline_name = incident.pipeline_name or "not provided"
    evidence_lines = "\n".join(f"- [{item.id}] {item.detail}" for item in diagnosis.evidence)
    facts = "\n".join(f"- {fact}" for fact in diagnosis.confirmed_facts)
    missing_evidence = "\n".join(f"- {item}" for item in diagnosis.missing_evidence)
    next_steps = "\n".join(
        f"{index}. {step}" for index, step in enumerate(diagnosis.recommended_next_steps, start=1)
    )
    playbook = diagnosis.suggested_playbook or "No playbook suggested"

    return f"""# Incident Report

## Incident

- Source: {incident.source_tool}
- Pipeline: {pipeline_name}
- Environment: {incident.environment}
- Classification: {diagnosis.triage.classification}
- Severity: {diagnosis.triage.severity.value}

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
