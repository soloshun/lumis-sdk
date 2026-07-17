"""Versioned, non-executing policy and playbook proposal contracts."""

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from .models import DomainModel
from .recovery import RiskLevel

POLICY_API_VERSION = "lumis.dev/v1"
LEGACY_POLICY_API_VERSION = "lumis.dev/v1alpha1"
PLAYBOOK_KIND = "Playbook"
POLICY_KIND = "RecoveryPolicy"


class ParameterType(StrEnum):
    """Primitive parameter types accepted by deterministic playbook actions."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"


class ParameterDefinition(DomainModel):
    """One typed and bounded action parameter."""

    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    type: ParameterType
    required: bool = True
    allowed_values: list[str | int | float | bool] = Field(default_factory=list, max_length=100)
    minimum: float | None = None
    maximum: float | None = None
    max_length: int | None = Field(default=None, ge=1, le=10_000)

    @model_validator(mode="after")
    def validate_bounds(self) -> "ParameterDefinition":
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum cannot exceed maximum")
        if (self.minimum is not None or self.maximum is not None) and self.type not in {
            ParameterType.INTEGER,
            ParameterType.NUMBER,
        }:
            raise ValueError("numeric bounds require an integer or number parameter")
        if self.max_length is not None and self.type is not ParameterType.STRING:
            raise ValueError("max_length requires a string parameter")
        for value in self.allowed_values:
            _validate_parameter_type(self.type, value)
        return self

    def validate_value(self, value: str | int | float | bool) -> None:
        """Fail closed when a proposal value violates this definition."""
        _validate_parameter_type(self.type, value)
        if self.allowed_values and value not in self.allowed_values:
            raise ValueError(f"parameter {self.name!r} is not in its allowlist")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if self.minimum is not None and value < self.minimum:
                raise ValueError(f"parameter {self.name!r} is below its minimum")
            if self.maximum is not None and value > self.maximum:
                raise ValueError(f"parameter {self.name!r} exceeds its maximum")
        if isinstance(value, str) and self.max_length is not None and len(value) > self.max_length:
            raise ValueError(f"parameter {self.name!r} exceeds max_length")


class PlaybookAction(DomainModel):
    """One allowlisted recommendation; it contains no executable implementation."""

    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_-]*$")
    summary: str = Field(min_length=1, max_length=2_000)
    risk: RiskLevel
    parameters: list[ParameterDefinition] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def require_unique_parameters(self) -> "PlaybookAction":
        names = [parameter.name for parameter in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("playbook action parameter names must be unique")
        return self


class DocumentMetadata(DomainModel):
    """Stable identity and revision for a policy document."""

    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_-]*$")
    version: str = Field(min_length=1, max_length=100)


class PlaybookDocument(DomainModel):
    """Strict versioned playbook made only of declarative action definitions."""

    api_version: str = Field(default=POLICY_API_VERSION, alias="apiVersion")
    kind: str = PLAYBOOK_KIND
    metadata: DocumentMetadata
    actions: list[PlaybookAction] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_document(self) -> "PlaybookDocument":
        if (
            self.api_version not in {POLICY_API_VERSION, LEGACY_POLICY_API_VERSION}
            or self.kind != PLAYBOOK_KIND
        ):
            raise ValueError("unsupported playbook apiVersion or kind")
        names = [action.name for action in self.actions]
        if len(names) != len(set(names)):
            raise ValueError("playbook action names must be unique")
        return self


class PolicyRule(DomainModel):
    """Deterministic policy for one pinned playbook action."""

    playbook_name: str
    action_name: str
    auto_approve_up_to: RiskLevel | None = None
    approval_required: bool = True

    @model_validator(mode="after")
    def protect_high_risk(self) -> "PolicyRule":
        if self.auto_approve_up_to is RiskLevel.HIGH:
            raise ValueError("high-risk actions can never be auto-approved")
        return self


class PolicyDocument(DomainModel):
    """Strict deterministic policy with an explicit default-deny posture."""

    api_version: str = Field(default=POLICY_API_VERSION, alias="apiVersion")
    kind: str = POLICY_KIND
    metadata: DocumentMetadata
    default_deny: bool = True
    rules: list[PolicyRule] = Field(default_factory=list, max_length=1_000)

    @model_validator(mode="after")
    def validate_document(self) -> "PolicyDocument":
        if (
            self.api_version not in {POLICY_API_VERSION, LEGACY_POLICY_API_VERSION}
            or self.kind != POLICY_KIND
        ):
            raise ValueError("unsupported policy apiVersion or kind")
        if not self.default_deny:
            raise ValueError("recovery policies must fail closed with default_deny=true")
        keys = [(rule.playbook_name, rule.action_name) for rule in self.rules]
        if len(keys) != len(set(keys)):
            raise ValueError("policy rules must target unique playbook actions")
        return self


class ProposalState(StrEnum):
    """Persistable lifecycle state for an immutable proposal revision."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class EvidenceReference(DomainModel):
    """Stable evidence identity included in a proposal snapshot."""

    id: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=200)
    digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class ActionProposal(DomainModel):
    """Immutable, attributable recommendation with no execution authority."""

    proposal_id: str = Field(min_length=1, max_length=200)
    revision: int = Field(default=1, ge=1)
    state: ProposalState
    diagnosis_id: str = Field(min_length=1, max_length=200)
    diagnosis_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=100)
    playbook_name: str
    playbook_version: str
    action_name: str
    policy_name: str
    policy_version: str
    risk: RiskLevel
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)
    approval_required: bool
    created_at: datetime
    expires_at: datetime
    execution_allowed: bool = False

    @model_validator(mode="after")
    def enforce_guardrails(self) -> "ActionProposal":
        if self.expires_at <= self.created_at:
            raise ValueError("proposal expires_at must be after created_at")
        if self.risk is RiskLevel.HIGH and not self.approval_required:
            raise ValueError("high-risk proposals always require approval")
        if self.execution_allowed:
            raise ValueError("Lumis SDK core proposals never grant execution authority")
        return self

    @property
    def canonical_digest(self) -> str:
        """Return a stable SHA-256 digest for replay and tamper checks."""
        return canonical_digest(self)


class DecisionStatus(StrEnum):
    """Human decision applied to a specific proposal revision."""

    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecisionRecord(DomainModel):
    """Idempotent, attributable decision for exactly one proposal revision."""

    decision_id: str = Field(min_length=1, max_length=200)
    proposal_id: str = Field(min_length=1, max_length=200)
    proposal_revision: int = Field(ge=1)
    status: DecisionStatus
    actor: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2_000)
    decided_at: datetime

    @property
    def canonical_digest(self) -> str:
        """Return a stable SHA-256 digest for idempotency and audit."""
        return canonical_digest(self)


def canonical_json(value: DomainModel | dict[str, Any]) -> str:
    """Serialize a public contract deterministically without Python-specific values."""
    payload = (
        value.model_dump(mode="json", by_alias=True) if isinstance(value, DomainModel) else value
    )
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_digest(value: DomainModel | dict[str, Any]) -> str:
    """Hash canonical JSON with SHA-256."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def playbook_json_schema() -> dict[str, Any]:
    """Return the generated JSON Schema for a playbook document."""
    return _versioned_schema(PlaybookDocument, POLICY_API_VERSION)


def policy_json_schema() -> dict[str, Any]:
    """Return the generated JSON Schema for a recovery policy document."""
    return _versioned_schema(PolicyDocument, POLICY_API_VERSION)


def legacy_playbook_json_schema() -> dict[str, Any]:
    """Return the frozen deprecated playbook schema."""
    return _versioned_schema(PlaybookDocument, LEGACY_POLICY_API_VERSION)


def legacy_policy_json_schema() -> dict[str, Any]:
    """Return the frozen deprecated recovery-policy schema."""
    return _versioned_schema(PolicyDocument, LEGACY_POLICY_API_VERSION)


def proposal_json_schema() -> dict[str, Any]:
    """Return the generated JSON Schema for an action proposal."""
    return ActionProposal.model_json_schema(by_alias=True)


def _versioned_schema(model: type[DomainModel], version: str) -> dict[str, Any]:
    schema = model.model_json_schema(by_alias=True)
    marker = schema["properties"]["apiVersion"]
    marker.pop("default", None)
    marker["const"] = version
    return schema


def _validate_parameter_type(
    expected: ParameterType,
    value: str | int | float | bool,
) -> None:
    matches = {
        ParameterType.STRING: isinstance(value, str),
        ParameterType.INTEGER: isinstance(value, int) and not isinstance(value, bool),
        ParameterType.NUMBER: isinstance(value, (int, float)) and not isinstance(value, bool),
        ParameterType.BOOLEAN: isinstance(value, bool),
    }
    if not matches[expected]:
        raise ValueError(f"value does not match parameter type {expected.value}")
