"""Strict configuration contracts for Lumis SDK projects and diagnosis rules."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lumis_sdk.domain import Severity

PROJECT_API_VERSION = "lumis.dev/v1alpha1"
PROJECT_KIND = "Project"
RULE_SET_KIND = "DiagnosisRuleSet"
DIAGNOSIS_RULE_KIND = "DiagnosisRule"


class StrictModel(BaseModel):
    """Base configuration model that rejects misspelled or unknown fields."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class MemoryConfig(StrictModel):
    """A project-owned local memory location."""

    provider: Literal["sqlite"] = "sqlite"
    path: str = ".lumis/incidents.db"


class ReportsConfig(StrictModel):
    """A project-owned report output location."""

    provider: Literal["markdown"] = "markdown"
    output_dir: str = Field(default=".lumis/reports", alias="outputDir")


class IncidentSourceConfig(StrictModel):
    """One configured local incident source for v1alpha1."""

    provider: Literal["local-log"]
    path: str


class RulesConfig(StrictModel):
    """Paths to versioned deterministic rule-set documents."""

    files: list[str] = Field(default_factory=list)


class ModelConfig(StrictModel):
    """Explicit model-assistance opt-in; disabled by default."""

    enabled: bool = False


class ObjectMetadata(StrictModel):
    """Portable object metadata shared by versioned configuration documents."""

    name: str = Field(min_length=1)
    labels: dict[str, str] = Field(default_factory=dict)


class DiagnosisRuleMetadata(ObjectMetadata):
    """Identity and revision metadata for one portable structured rule."""

    version: str = Field(default="1", min_length=1)


class ProjectSpec(StrictModel):
    """The v1alpha1 project specification."""

    environment: str = "local"
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    reports: ReportsConfig = Field(default_factory=ReportsConfig)
    incident_sources: list[IncidentSourceConfig] = Field(
        default_factory=list, alias="incidentSources"
    )
    rules: RulesConfig = Field(default_factory=RulesConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)


class ProjectDocument(StrictModel):
    """Versioned Lumis SDK project configuration document."""

    api_version: Literal["lumis.dev/v1alpha1"] = Field(alias="apiVersion")
    kind: Literal["Project"]
    metadata: ObjectMetadata
    spec: ProjectSpec


class DeterministicRule(StrictModel):
    """A reproducible diagnosis rule supplied by a consuming project."""

    name: str = Field(min_length=1)
    rule_id: str = Field(alias="id", min_length=1)
    version: str = "1"
    priority: int = 0
    all_contains: list[str] = Field(min_length=1)
    classification: str
    severity: Severity
    summary: str
    root_cause_hypothesis: str
    confidence: float = Field(ge=0, le=1)
    missing_evidence: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    suggested_playbook: str | None = None

    @property
    def stable_id(self) -> str:
        """Return the required public rule identity."""
        return self.rule_id


class RuleCondition(StrictModel):
    """One typed comparison against a dot-addressable incident field."""

    field: str = Field(min_length=1)
    contains: str | None = None
    equals: str | int | float | bool | None = None
    prefix: str | None = None
    matches_regex: str | None = Field(default=None, alias="matchesRegex")
    greater_than: float | None = Field(default=None, alias="greaterThan")
    greater_than_or_equal: float | None = Field(default=None, alias="greaterThanOrEqual")
    less_than: float | None = Field(default=None, alias="lessThan")
    less_than_or_equal: float | None = Field(default=None, alias="lessThanOrEqual")

    @model_validator(mode="after")
    def require_exactly_one_operator(self) -> "RuleCondition":
        operators = (
            self.contains,
            self.equals,
            self.prefix,
            self.matches_regex,
            self.greater_than,
            self.greater_than_or_equal,
            self.less_than,
            self.less_than_or_equal,
        )
        if sum(value is not None for value in operators) != 1:
            raise ValueError("a condition must define exactly one comparison operator")
        if self.matches_regex is not None:
            try:
                re.compile(self.matches_regex)
            except re.error as error:
                raise ValueError(f"matchesRegex is invalid: {error}") from error
        return self


class CompoundRuleMatch(StrictModel):
    """Boolean condition groups evaluated without provider-specific logic."""

    all: list[RuleCondition] = Field(default_factory=list)
    any: list[RuleCondition] = Field(default_factory=list)
    not_: list[RuleCondition] = Field(default_factory=list, alias="not")

    @model_validator(mode="after")
    def require_at_least_one_condition(self) -> "CompoundRuleMatch":
        if not self.all and not self.any and not self.not_:
            raise ValueError("match must define at least one condition in all, any, or not")
        return self


class StructuredRuleDiagnosis(StrictModel):
    """Diagnosis returned when a structured deterministic rule wins."""

    classification: str = Field(min_length=1)
    severity: Severity = Severity.MEDIUM
    summary: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    confirmed_facts: list[str] = Field(default_factory=list, alias="confirmedFacts")


class RuleEvidenceRequirements(StrictModel):
    """Evidence kinds that must be present before a rule can match."""

    required: list[str] = Field(default_factory=list)


class StructuredDiagnosisRuleSpec(StrictModel):
    """Behavior and result contract for one structured rule."""

    priority: int = 0
    match: CompoundRuleMatch
    diagnosis: StructuredRuleDiagnosis
    evidence: RuleEvidenceRequirements = Field(default_factory=RuleEvidenceRequirements)
    recommended_next_steps: list[str] = Field(default_factory=list, alias="recommendedNextSteps")
    suggested_playbook: str | None = Field(default=None, alias="suggestedPlaybook")


class DiagnosisRuleDocument(StrictModel):
    """One strict, versioned, portable compound diagnosis rule."""

    api_version: Literal["lumis.dev/v1alpha1"] = Field(alias="apiVersion")
    kind: Literal["DiagnosisRule"]
    metadata: DiagnosisRuleMetadata
    spec: StructuredDiagnosisRuleSpec

    @property
    def stable_id(self) -> str:
        """Return the metadata name used as the stable public rule ID."""
        return self.metadata.name

    @property
    def specificity(self) -> int:
        """Return the documented deterministic tie-break score."""
        return (
            len(self.spec.match.all) * 2
            + len(self.spec.match.any)
            + len(self.spec.match.not_)
            + len(self.spec.evidence.required)
        )


class RuleSetSpec(StrictModel):
    """Rules carried by a versioned rule-set document."""

    rules: list[DeterministicRule] = Field(default_factory=list)


class DiagnosisRuleSetDocument(StrictModel):
    """Versioned deterministic rule-set configuration document."""

    api_version: Literal["lumis.dev/v1alpha1"] = Field(alias="apiVersion")
    kind: Literal["DiagnosisRuleSet"]
    metadata: ObjectMetadata
    spec: RuleSetSpec


class LumisConfig(StrictModel):
    """Resolved runtime configuration used by the CLI and Python API."""

    project: str
    environment: str = "local"
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    reports: ReportsConfig = Field(default_factory=ReportsConfig)
    incident_sources: list[IncidentSourceConfig] = Field(default_factory=list)
    rules_files: list[str] = Field(default_factory=list)
    rules: list[DeterministicRule] = Field(default_factory=list)
    structured_rules: list[DiagnosisRuleDocument] = Field(default_factory=list)
    model: ModelConfig = Field(default_factory=ModelConfig)
    source_api_version: Literal["lumis.dev/v1alpha1"] = "lumis.dev/v1alpha1"
