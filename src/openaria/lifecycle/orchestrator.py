"""One safe, non-executing lifecycle orchestration function."""

from collections.abc import Callable
from pathlib import Path

from openaria.lifecycle.contracts import (
    ApprovalProvider,
    AuditTrail,
    ContextProvider,
    PolicyEngine,
    Verifier,
)
from openaria.lifecycle.models import (
    ActionPlan,
    ApprovalDecision,
    AuditEvent,
    LifecycleResult,
    VerificationResult,
)
from openaria.memory import SQLiteIncidentStore
from openaria.reports import render_markdown_report
from openaria.schemas import DiagnosisResult, IncidentInput


def run_lifecycle(
    incident: IncidentInput,
    *,
    context_provider: ContextProvider,
    policy_engine: PolicyEngine,
    approval_provider: ApprovalProvider,
    verifier: Verifier,
    audit_trail: AuditTrail,
    diagnoser: Callable[[str], DiagnosisResult],
    memory_store: SQLiteIncidentStore | None = None,
    report_path: Path | None = None,
) -> LifecycleResult:
    """Run a diagnosis, proposal, approval, verification, and memory update.

    This function intentionally stops at a recommendation-only action plan. It
    models the lifecycle boundaries needed by cookbooks without executing a
    command, changing an external system, or requiring a model provider.
    """
    audit_events: list[AuditEvent] = []
    context = context_provider.get_context(incident)
    _record(
        audit_trail,
        audit_events,
        "context_retrieved",
        f"Retrieved {len(context.items)} synthetic context items.",
    )

    raw_log = incident.raw_payload.get("log", "")
    diagnosis = diagnoser(str(raw_log))
    _record(audit_trail, audit_events, "diagnosis_completed", diagnosis.triage.classification)

    plan = policy_engine.propose(diagnosis, context)
    _record(audit_trail, audit_events, "plan_proposed", plan.playbook_name)

    approval = approval_provider.request(plan)
    _record(audit_trail, audit_events, "approval_recorded", approval.status.value)

    verification = verifier.verify(plan, approval)
    _record(audit_trail, audit_events, "verification_recorded", verification.status.value)

    stored_incident_id: str | None = None
    if memory_store is not None and report_path is not None:
        report = _render_lifecycle_report(incident, diagnosis, plan, approval, verification)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        stored = memory_store.save(incident, diagnosis, report, report_path)
        stored_incident_id = stored.id
        _record(audit_trail, audit_events, "memory_updated", stored.id)

    return LifecycleResult(
        incident=incident,
        context=context,
        diagnosis=diagnosis,
        action_plan=plan,
        approval=approval,
        verification=verification,
        audit_events=audit_events,
        stored_incident_id=stored_incident_id,
    )


def _record(
    audit_trail: AuditTrail,
    events: list[AuditEvent],
    event_type: str,
    detail: str,
) -> None:
    """Record a lifecycle transition through the injected audit boundary."""
    event = AuditEvent(event_type=event_type, detail=detail)
    audit_trail.record(event)
    events.append(event)


def _render_lifecycle_report(
    incident: IncidentInput,
    diagnosis: DiagnosisResult,
    plan: ActionPlan,
    approval: ApprovalDecision,
    verification: VerificationResult,
) -> str:
    """Append guarded-lifecycle state to the standard Markdown diagnosis report."""
    base_report = render_markdown_report(incident, diagnosis).rstrip()
    return f"""{base_report}

## Proposed Playbook

- Name: `{plan.playbook_name}`
- Risk: {plan.risk_level.value}
- Approval required: {plan.approval_required}
- Execution allowed: {plan.execution_allowed}

{plan.summary}

## Approval

- Status: {approval.status.value}
- Approver: {approval.approver or "not provided"}
- Reason: {approval.reason or "not provided"}

## Verification

- Status: {verification.status.value}
- Notes: {verification.notes}
"""
