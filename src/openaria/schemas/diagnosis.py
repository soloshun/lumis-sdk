"""Triage and diagnosis result models."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """The urgency assigned to an incident."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceItem(BaseModel):
    """A claim-supported observation from supplied incident context."""

    id: str
    source: str
    detail: str
    confidence: float = Field(ge=0, le=1)


class TriageResult(BaseModel):
    """A deterministic first-pass classification of an incident."""

    classification: str
    severity: Severity
    summary: str
    missing_context: list[str] = Field(default_factory=list)


class DiagnosisResult(BaseModel):
    """An evidence-grounded diagnosis that separates facts from hypotheses."""

    triage: TriageResult
    confirmed_facts: list[str] = Field(default_factory=list)
    root_cause_hypothesis: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    suggested_playbook: str | None = None
