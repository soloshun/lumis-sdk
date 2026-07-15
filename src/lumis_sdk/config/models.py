"""Strict configuration contracts for Lumis SDK projects and diagnosis rules."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lumis_sdk.domain import Severity

PROJECT_API_VERSION = "lumis.dev/v1alpha1"
PROJECT_KIND = "Project"
RULE_SET_KIND = "DiagnosisRuleSet"


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
    model: ModelConfig = Field(default_factory=ModelConfig)
    source_api_version: Literal["lumis.dev/v1alpha1"] = "lumis.dev/v1alpha1"
