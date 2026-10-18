"""Deterministic human-readable reports; untrusted text cannot supply Markdown links/HTML."""

import html
import re

from lumis_sdk.investigation.contracts import IncidentReport
from lumis_sdk.security.redaction import redact_text


def _text(value: object) -> str:
    safe = html.escape(redact_text(str(value)), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", safe).replace("\n", " ")


def report_markdown(report: IncidentReport) -> str:
    evidence = {item.id: index for index, item in enumerate(report.context.evidence, 1)}
    receipts = {item.id: index for index, item in enumerate(report.receipts, 1)}

    def citations(eids: tuple[str, ...] = (), rids: tuple[str, ...] = ()) -> str:
        return (
            " ".join(
                [f"[{_text(identity)}](#evidence-{evidence[identity]})" for identity in eids]
                + [f"[{_text(identity)}](#receipt-{receipts[identity]})" for identity in rids]
            )
            or "No usable evidence cited."
        )

    event = report.context.incident
    lines = [
        f"# Incident {_text(event.id)}",
        "",
        "Unconfirmed hypotheses only. Human review required; no fix has been executed.",
        "",
        "## Observation context",
        "",
        f"Window: {_text(event.started_at.isoformat())} → {_text(event.ended_at.isoformat())}.",
        "These are evidence-window bounds, not measured fault onset or resolution.",
        "",
        "Caller-reported symptoms (context, not independently verified facts):",
        "",
        *[f"- {_text(symptom)}" for symptom in event.symptoms],
        "",
        f"Route: {_text(report.route)}; conclusion: {_text(report.conclusion)}; "
        f"stop: {_text(report.stop_reason)}.",
        "",
        "## Deterministic findings",
        "",
    ]
    for finding in report.findings:
        state = finding.assessment
        lines.append(
            f"- {_text(finding.rule_id)}: {_text(finding.display_status)}. "
            + citations((*state.supporting_evidence_ids, *state.contradicting_evidence_ids))
        )
        for check in state.missing_checks:
            lines.append(
                f"  - Still needed: {_text(check.entity_id)}/{_text(check.key)} "
                f"{_text(check.operator)} {_text(check.value)} (usable evidence missing)."
            )
    if not report.findings:
        lines.append("No in-scope signatures evaluated.")
    lines += ["", "## Candidate explanations", ""]
    for assessment in report.assessments:
        candidate = assessment.hypothesis
        lines += [
            f"### {_text(candidate.id)} — {_text(assessment.display_state)}",
            "",
            f"Proposed explanation: {_text(candidate.statement)}",
            "",
            "Proposed path (not proof of connected or causal edges): "
            + " → ".join(_text(identity) for identity in candidate.causal_path)
            + ".",
            "",
            "Supporting check observations: " + citations(assessment.supporting_evidence_ids),
            "",
            "Ruling-out observations: " + citations(assessment.contradicting_evidence_ids),
            "",
        ]
        if assessment.missing_checks:
            lines += [
                "Still needed to decide:",
                "",
                *[
                    f"- {_text(check.entity_id)}/{_text(check.key)} "
                    f"{_text(check.operator)} {_text(check.value)} (usable evidence missing)."
                    for check in assessment.missing_checks
                ],
                "",
            ]
    if not report.assessments:
        lines.append("No accepted candidate explanations.")
    lines += ["", "## Open questions and tentative suggestions", ""]
    lines += [f"- {_text(question)}" for question in report.unresolved_questions]
    for suggestion in report.suggestions:
        lines.append(
            f"- Tentative suggestion for {_text(suggestion.hypothesis_id)}: "
            f"{_text(suggestion.description)} "
            + citations(suggestion.evidence_ids, suggestion.receipt_ids)
        )
        if suggestion.patch:
            lines.append(
                "  Patch text is in the JSON report for separate manual review; not applied."
            )
    if not report.unresolved_questions and not report.suggestions:
        lines.append(
            "No additional questions or suggestions recorded; causality remains unconfirmed."
        )
    lines += ["", "## Authoring warnings", ""]
    lines += [f"- {_text(warning)}" for warning in report.warnings] or ["None recorded."]
    lines += ["", "## Evidence ledger", ""]
    for item in report.context.evidence:
        raw = str(item.value)
        value = _text(raw[:400]) + (" [excerpt; see JSON]" if len(raw) > 400 else "")
        lines += [
            f'<a id="evidence-{evidence[item.id]}"></a>',
            "",
            f"- {_text(item.id)}: {_text(item.entity_id)}/{_text(item.key)} = {value}; "
            f"query {_text(item.query_id)}, quality {_text(item.quality)}, "
            f"source {_text(item.source)}, at {_text(item.observed_at.isoformat())}.",
            "",
        ]
    if not evidence:
        lines.append("No observations collected.")
    lines += ["", "## Inspection receipts", ""]
    for receipt in report.receipts:
        lines += [
            f'<a id="receipt-{receipts[receipt.id]}"></a>',
            "",
            f"- {_text(receipt.id)}: {_text(receipt.operation)} / {_text(receipt.status)}; "
            f"{_text(receipt.purpose)}; reason {_text(receipt.reason_code or 'none')}; "
            f"truncated {_text(receipt.truncated)}; "
            f"cached from {_text(receipt.cached_from or 'none')}.",
            f"  Full safe-output SHA-256: {_text(receipt.digest)}; "
            f"visible-output SHA-256: {_text(receipt.output_digest or 'not recorded')}.",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"
