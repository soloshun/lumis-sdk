"""Bounded loading for strict, versioned Lumis SDK configuration."""

import json
from pathlib import Path
from typing import Any

import yaml

from .models import (
    DeterministicRule,
    DiagnosisRuleDocument,
    DiagnosisRuleSetDocument,
    LumisConfig,
    ProjectDocument,
)

MAX_CONFIG_BYTES = 1_048_576


def load_config(path: Path) -> LumisConfig:
    """Load a strict project and its legacy rule sets or structured rule documents."""
    config = _runtime_from_versioned(ProjectDocument.model_validate(_load_mapping(path)))

    rules: list[DeterministicRule] = [*config.rules]
    structured_rules: list[DiagnosisRuleDocument] = [*config.structured_rules]
    for configured_path in config.rules_files:
        rule_path = resolve_project_path(path, configured_path)
        raw = _load_mapping(rule_path)
        kind = raw.get("kind")
        if kind == "DiagnosisRuleSet":
            rules.extend(DiagnosisRuleSetDocument.model_validate(raw).spec.rules)
        elif kind == "DiagnosisRule":
            structured_rules.append(DiagnosisRuleDocument.model_validate(raw))
        else:
            raise ValueError(f"Unsupported rule document kind {kind!r}: {rule_path}")
    if rules and structured_rules:
        raise ValueError(
            "A project cannot mix DiagnosisRuleSet and DiagnosisRule files; "
            "migrate the complete rule collection together."
        )
    return config.model_copy(update={"rules": rules, "structured_rules": structured_rules})


def load_rules_file(path: Path) -> list[DeterministicRule]:
    """Load one strict v1alpha1 diagnosis rule-set document."""
    return DiagnosisRuleSetDocument.model_validate(_load_mapping(path)).spec.rules


def load_diagnosis_rule(path: Path) -> DiagnosisRuleDocument:
    """Load one strict v1alpha1 structured diagnosis-rule document."""
    return DiagnosisRuleDocument.model_validate(_load_mapping(path))


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


def diagnosis_rule_json_schema() -> dict[str, Any]:
    """Return the checked schema for a single structured diagnosis rule."""
    return DiagnosisRuleDocument.model_json_schema(by_alias=True)


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
