"""Stable, vendor-neutral domain models for incidents and diagnoses."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    """Strict base for public Lumis SDK domain contracts."""

    model_config = ConfigDict(extra="forbid")


class Severity(StrEnum):
    """The urgency assigned to an incident."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DiagnosisMethod(StrEnum):
    """The mechanism that produced a diagnosis."""

    DETERMINISTIC = "deterministic"
    RETRIEVAL = "retrieval"
    MODEL_ASSISTED = "model_assisted"
    HYBRID = "hybrid"
    ESCALATED = "escalated"


class TruthState(StrEnum):
    """The confirmation state of retained operational knowledge."""

    UNCONFIRMED_HYPOTHESIS = "unconfirmed_hypothesis"
    HUMAN_CONFIRMED = "human_confirmed"
    VERIFICATION_CONFIRMED = "verification_confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class IncidentInput(DomainModel):
    """A vendor-neutral representation of a received incident."""

    source_tool: str
    pipeline_name: str | None = None
    environment: str = "local"
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(DomainModel):
    """A claim-supported observation from supplied incident context."""

    id: str
    source: str
    detail: str
    confidence: float = Field(ge=0, le=1)
    kind: str = "observation"
    reference: str | None = None
    observed_at: datetime | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class Hypothesis(DomainModel):
    """An uncertain causal statement linked to supporting and conflicting evidence."""

    statement: str
    confidence: float = Field(ge=0, le=1)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)


class TriageResult(DomainModel):
    """A deterministic first-pass classification of an incident."""

    classification: str
    severity: Severity
    summary: str
    missing_context: list[str] = Field(default_factory=list)


class DiagnosisResult(DomainModel):
    """An evidence-grounded diagnosis produced by one declared method."""

    triage: TriageResult
    confirmed_facts: list[str] = Field(default_factory=list)
    root_cause_hypothesis: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    suggested_playbook: str | None = None
    method: DiagnosisMethod = DiagnosisMethod.DETERMINISTIC
    requires_human_review: bool = True


class ConfirmedResolution(DomainModel):
    """A human- or verification-confirmed outcome; never inferred from model text."""

    incident_id: UUID
    confirmed_root_cause: str
    action_taken: str
    outcome: str
    verified: bool
    confirmed_by: str
    confirmed_at: datetime
    reusable_notes: list[str] = Field(default_factory=list)
    truth_state: TruthState = TruthState.HUMAN_CONFIRMED
