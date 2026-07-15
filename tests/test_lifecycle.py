"""Tests for canonical guarded lifecycle orchestration."""

from lumis_sdk.adapters.deterministic import diagnose_text
from lumis_sdk.adapters.incidents import incident_from_log
from lumis_sdk.application import run_guarded_lifecycle
from lumis_sdk.config import DeterministicRule
from lumis_sdk.domain import (
    ActionPlan,
    ApprovalDecision,
    ApprovalStatus,
    AuditEvent,
    ContextItem,
    ContextKind,
    IncidentContext,
    RiskLevel,
    VerificationResult,
    VerificationStatus,
)


class FixtureContextProvider:
    def get_context(self, incident: object) -> IncidentContext:
        assert hasattr(incident, "source_tool")
        return IncidentContext(
            incident=incident,
            items=[
                ContextItem(id="ctx-1", kind=ContextKind.LOGS, source="fixture", content="failure")
            ],
        )


class FixturePolicy:
    def propose(self, diagnosis: object, context: object) -> ActionPlan:
        return ActionPlan(
            playbook_name="configured_playbook",
            risk_level=RiskLevel.MEDIUM,
            approval_required=True,
            summary="A project supplied this plan.",
        )


class FixtureApproval:
    def request(self, plan: object) -> ApprovalDecision:
        return ApprovalDecision(status=ApprovalStatus.APPROVED, approver="reviewer")


class FixtureVerifier:
    def verify(self, plan: object, approval: object) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.NOT_RUN,
            checks=["No execution capability exists."],
            notes="Recommendation-only framework run.",
        )


class FixtureAuditTrail:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


def test_lifecycle_uses_only_injected_project_adapters() -> None:
    """The application lifecycle composes only canonical ports."""
    rule = DeterministicRule(
        id="fixture-rule",
        name="fixture-rule",
        all_contains=["FAILURE_CODE"],
        classification="configured_failure",
        severity="medium",
        summary="A configured failure occurred.",
        root_cause_hypothesis="The fixture rule matched.",
        confidence=0.5,
    )
    incident = incident_from_log("FAILURE_CODE", "fixture.log", "fixture-project")
    audit_trail = FixtureAuditTrail()
    result = run_guarded_lifecycle(
        incident,
        context_provider=FixtureContextProvider(),
        policy_evaluator=FixturePolicy(),
        approval_provider=FixtureApproval(),
        verifier=FixtureVerifier(),
        audit_trail=audit_trail,
        diagnoser=lambda text: diagnose_text(text, [rule]),
    )

    assert result.diagnosis.triage.classification == "configured_failure"
    assert result.action_plan.playbook_name == "configured_playbook"
    assert result.verification.status is VerificationStatus.NOT_RUN
    assert audit_trail.events == result.audit_events
