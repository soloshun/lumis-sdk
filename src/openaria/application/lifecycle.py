"""Application orchestration for a guarded, non-executing recovery proposal."""

from collections.abc import Callable

from openaria.domain import AuditEvent, DiagnosisResult, IncidentInput, LifecycleResult
from openaria.ports import (
    ApprovalProvider,
    AuditTrail,
    ContextProvider,
    PolicyEvaluator,
    RecoveryVerifier,
)


def run_guarded_lifecycle(
    incident: IncidentInput,
    *,
    context_provider: ContextProvider,
    policy_evaluator: PolicyEvaluator,
    approval_provider: ApprovalProvider,
    verifier: RecoveryVerifier,
    audit_trail: AuditTrail,
    diagnoser: Callable[[str], DiagnosisResult],
) -> LifecycleResult:
    """Run context, diagnosis, proposal, approval, and verification without actuation."""
    events: list[AuditEvent] = []
    context = context_provider.get_context(incident)
    _record(audit_trail, events, "context_retrieved", f"Retrieved {len(context.items)} items.")
    diagnosis = diagnoser(str(incident.raw_payload.get("log", "")))
    _record(audit_trail, events, "diagnosis_completed", diagnosis.triage.classification)
    plan = policy_evaluator.propose(diagnosis, context)
    _record(audit_trail, events, "plan_proposed", plan.playbook_name)
    approval = approval_provider.request(plan)
    _record(audit_trail, events, "approval_recorded", approval.status.value)
    verification = verifier.verify(plan, approval)
    _record(audit_trail, events, "verification_recorded", verification.status.value)
    return LifecycleResult(
        incident=incident,
        context=context,
        diagnosis=diagnosis,
        action_plan=plan,
        approval=approval,
        verification=verification,
        audit_events=events,
    )


def _record(
    audit_trail: AuditTrail,
    events: list[AuditEvent],
    event_type: str,
    detail: str,
) -> None:
    event = AuditEvent(event_type=event_type, detail=detail)
    audit_trail.record(event)
    events.append(event)
