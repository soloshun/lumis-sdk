"""Conservative evidence-backed triage before any model is invoked."""

from typing import Literal, Protocol

from lumis_sdk.core import IncidentContext
from lumis_sdk.core.contracts import validate_hypothesis
from lumis_sdk.investigation.contracts import DiagnosticRule, Finding
from lumis_sdk.reasoning import assess


class TriageGuard(Protocol):
    """Optional caller-owned additional sufficiency checks; never used by the agent."""

    def allows(self, rule: DiagnosticRule, context: IncidentContext) -> bool: ...


def evaluate_checks(
    rules: tuple[DiagnosticRule, ...], context: IncidentContext
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for rule in rules:
        validate_hypothesis(rule.hypothesis, context)
        assessment = assess(rule.hypothesis, context, ("deterministic",))
        status: Literal["match", "no_match", "unknown"] = (
            "match"
            if assessment.state == "supported"
            else "no_match"
            if assessment.state == "contradicted"
            else "unknown"
        )
        findings.append(
            Finding(
                rule_id=rule.id,
                status=status,
                terminal=rule.terminal,
                assessment=assessment,
            )
        )
    return tuple(findings)


def sufficient_finding(
    rules: tuple[DiagnosticRule, ...],
    findings: tuple[Finding, ...],
    context: IncidentContext,
    guard: TriageGuard | None = None,
) -> Finding | None:
    """Exactly one supported terminal finding; full scope and no competing unknown/match."""
    viable = [finding for finding in findings if finding.status != "no_match"]
    if len(viable) != 1 or viable[0].status != "match" or not viable[0].terminal:
        return None
    finding = viable[0]
    rule = next(rule for rule in rules if rule.id == finding.rule_id)
    if not set(context.incident.affected_entities) <= set(rule.explains_entities):
        return None
    if guard is not None and not guard.allows(rule, context):
        return None
    return finding
