"""Transport-neutral contracts for guarded recovery state."""

from enum import StrEnum

from pydantic import Field

from .models import DiagnosisResult, DomainModel, IncidentInput


class ContextKind(StrEnum):
    """The categories of evidence a provider may expose."""

    LOGS = "logs"
    METRICS = "metrics"
    LINEAGE = "lineage"
    SCHEMA = "schema"
    RUNBOOK = "runbook"
    PLAYBOOK = "playbook"
    CODE = "code"
    VERIFICATION = "verification"


class ContextItem(DomainModel):
    """One bounded piece of incident context."""

    id: str
    kind: ContextKind
    source: str
    content: str


class IncidentContext(DomainModel):
    """Evidence returned by a context provider for one incident."""

    incident: IncidentInput
    items: list[ContextItem] = Field(default_factory=list)


class RiskLevel(StrEnum):
    """Risk tier assigned to a proposed action."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionPlan(DomainModel):
    """A recommendation-only plan selected from an allowlisted playbook."""

    playbook_name: str
    risk_level: RiskLevel
    approval_required: bool
    summary: str
    steps: list[str] = Field(default_factory=list)
    execution_allowed: bool = False


class ApprovalStatus(StrEnum):
    """The result of an explicit approval decision."""

    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class ApprovalDecision(DomainModel):
    """A recorded approval decision for a proposed plan."""

    status: ApprovalStatus
    approver: str | None = None
    reason: str | None = None


class VerificationStatus(StrEnum):
    """The state of a bounded verification check."""

    NOT_RUN = "not_run"
    SKIPPED = "skipped"
    PASSED = "passed"
    FAILED = "failed"


class VerificationResult(DomainModel):
    """A bounded result from a verification provider."""

    status: VerificationStatus
    checks: list[str] = Field(default_factory=list)
    notes: str


class AuditEvent(DomainModel):
    """A local, inspectable lifecycle transition."""

    event_type: str
    detail: str


class LifecycleResult(DomainModel):
    """Complete output of one non-executing OpenARIA lifecycle run."""

    incident: IncidentInput
    context: IncidentContext
    diagnosis: DiagnosisResult
    action_plan: ActionPlan
    approval: ApprovalDecision
    verification: VerificationResult
    audit_events: list[AuditEvent] = Field(default_factory=list)
    stored_incident_id: str | None = None
