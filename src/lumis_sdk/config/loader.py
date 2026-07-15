"""Bounded loading for strict, versioned Lumis SDK configuration."""

import json
from pathlib import Path
from typing import Any

import yaml

from .models import (
    DeterministicRule,
    DiagnosisRuleSetDocument,
    LumisConfig,
    ProjectDocument,
)

MAX_CONFIG_BYTES = 1_048_576


def load_config(path: Path) -> LumisConfig:
    """Load a strict v1alpha1 project and each referenced versioned rule set."""
    config = _runtime_from_versioned(ProjectDocument.model_validate(_load_mapping(path)))

    rules: list[DeterministicRule] = [*config.rules]
    for configured_path in config.rules_files:
        rules.extend(load_rules_file(resolve_project_path(path, configured_path)))
    return config.model_copy(update={"rules": rules})


def load_rules_file(path: Path) -> list[DeterministicRule]:
    """Load one strict v1alpha1 diagnosis rule-set document."""
    return DiagnosisRuleSetDocument.model_validate(_load_mapping(path)).spec.rules


def resolve_project_path(config_path: Path, configured_path: str) -> Path:
    """Resolve and normalize a configured project path relative to its YAML file."""
    path = Path(configured_path)
    return (path if path.is_absolute() else config_path.parent / path).resolve()


def project_json_schema() -> dict[str, Any]:
    """Return the checked configuration schema for tooling and editors."""
    return ProjectDocument.model_json_schema(by_alias=True)


def rules_json_schema() -> dict[str, Any]:
    """Return the checked diagnosis rule-set schema for tooling and editors."""
    return DiagnosisRuleSetDocument.model_json_schema(by_alias=True)


def _runtime_from_versioned(document: ProjectDocument) -> LumisConfig:
    return LumisConfig(
        project=document.metadata.name,
        environment=document.spec.environment,
        memory=document.spec.memory,
        reports=document.spec.reports,
        incident_sources=document.spec.incident_sources,
        rules_files=document.spec.rules.files,
        model=document.spec.model,
        source_api_version=document.api_version,
    )


def _load_mapping(path: Path) -> dict[str, Any]:
    raw = _load_data(path)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a mapping at the root of configuration: {path}")
    return raw


def _load_data(path: Path) -> Any:
    size = path.stat().st_size
    if size > MAX_CONFIG_BYTES:
        raise ValueError(f"Configuration exceeds {MAX_CONFIG_BYTES} bytes: {path}")
    with path.open(encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            return json.load(handle)
        return yaml.safe_load(handle) or {}
