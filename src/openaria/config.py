"""Configuration models and YAML loading for OpenARIA projects."""

import json
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from openaria.schemas import Severity


class MemoryConfig(BaseModel):
    """A project-owned local memory location."""

    path: str = ".openaria/incidents.db"


class ReportsConfig(BaseModel):
    """A project-owned report output location."""

    output_dir: str = ".openaria/reports"


class TelemetryConfig(BaseModel):
    """Project-owned local telemetry input locations."""

    log: str | None = None


class DeterministicRule(BaseModel):
    """A data-driven diagnosis rule supplied by a consuming project."""

    name: str
    all_contains: list[str] = Field(min_length=1)
    classification: str
    severity: Severity
    summary: str
    root_cause_hypothesis: str
    confidence: float = Field(ge=0, le=1)
    missing_evidence: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    suggested_playbook: str | None = None


class OpenARIAConfig(BaseModel):
    """The portable configuration surface for an OpenARIA project."""

    project: str
    environment: str = "local"
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    reports: ReportsConfig = Field(default_factory=ReportsConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    rules_file: str | None = None
    rules: list[DeterministicRule] = Field(default_factory=list)


def load_config(path: Path) -> OpenARIAConfig:
    """Load and validate an OpenARIA YAML project configuration."""
    with path.open(encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file) or {}
    config = OpenARIAConfig.model_validate(raw_config)
    if config.rules_file is None:
        return config

    rules_path = resolve_project_path(path, config.rules_file)
    return config.model_copy(update={"rules": [*config.rules, *load_rules_file(rules_path)]})


def load_rules_file(path: Path) -> list[DeterministicRule]:
    """Load rule definitions from a YAML or JSON file."""
    with path.open(encoding="utf-8") as rules_handle:
        if path.suffix.lower() == ".json":
            raw_rules = json.load(rules_handle)
        else:
            raw_rules = yaml.safe_load(rules_handle) or {}

    rule_items = raw_rules["rules"] if isinstance(raw_rules, dict) else raw_rules
    return [DeterministicRule.model_validate(rule) for rule in rule_items]


def resolve_project_path(config_path: Path, configured_path: str) -> Path:
    """Resolve a configured project path relative to its YAML file."""
    path = Path(configured_path)
    return path if path.is_absolute() else config_path.parent / path
