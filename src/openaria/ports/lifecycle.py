"""Provider contracts for guarded recovery lifecycle boundaries."""

from typing import Protocol

from openaria.domain import (
    ActionPlan,
    ApprovalDecision,
    AuditEvent,
    DiagnosisResult,
    IncidentContext,
    IncidentInput,
    VerificationResult,
)


class ContextProvider(Protocol):
    """Retrieve bounded evidence without mutating the incident estate."""

    def get_context(self, incident: IncidentInput) -> IncidentContext: ...


class PolicyEvaluator(Protocol):
    """Select a recommendation-only action plan from allowed playbooks."""

    def propose(self, diagnosis: DiagnosisResult, context: IncidentContext) -> ActionPlan: ...


class ApprovalProvider(Protocol):
    """Record an explicit approval decision."""

    def request(self, plan: ActionPlan) -> ApprovalDecision: ...


class RecoveryVerifier(Protocol):
    """Return verification state without performing remediation."""

    def verify(self, plan: ActionPlan, approval: ApprovalDecision) -> VerificationResult: ...


class AuditTrail(Protocol):
    """Record lifecycle transitions for inspection."""

    def record(self, event: AuditEvent) -> None: ...
