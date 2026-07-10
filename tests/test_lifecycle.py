"""Tests for lifecycle orchestration using project-supplied adapters."""

from pathlib import Path

from openaria.config import DeterministicRule
from openaria.incidents import incident_from_log
from openaria.lifecycle import (
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
    run_lifecycle,
)
from openaria.memory import SQLiteIncidentStore
from openaria.triage import diagnose_text


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


def test_lifecycle_uses_only_injected_project_adapters(tmp_path: Path) -> None:
    """The framework does not need a built-in scenario to run a lifecycle."""
    rule = DeterministicRule(
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
    store = SQLiteIncidentStore(tmp_path / "incidents.db")
    result = run_lifecycle(
        incident,
        context_provider=FixtureContextProvider(),
        policy_engine=FixturePolicy(),
        approval_provider=FixtureApproval(),
        verifier=FixtureVerifier(),
        audit_trail=audit_trail,
        diagnoser=lambda text: diagnose_text(text, [rule]),
        memory_store=store,
        report_path=tmp_path / "report.md",
    )

    assert result.diagnosis.triage.classification == "configured_failure"
    assert result.action_plan.playbook_name == "configured_playbook"
    assert result.stored_incident_id is not None
    assert result.verification.status is VerificationStatus.NOT_RUN
