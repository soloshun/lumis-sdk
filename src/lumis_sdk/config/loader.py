"""Bounded loading for strict, versioned Lumis SDK configuration."""

import json
import warnings
from pathlib import Path
from typing import Any, cast

import yaml
from yaml.events import AliasEvent
from yaml.nodes import Node

from .models import (
    LEGACY_PROJECT_API_VERSION,
    PROJECT_API_VERSION,
    DeterministicRule,
    DiagnosisRuleDocument,
    DiagnosisRuleSetDocument,
    LumisConfig,
    ProjectDocument,
)

MAX_CONFIG_BYTES = 1_048_576
MAX_CONFIG_DEPTH = 64


class BoundedSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects aliases and excessive nesting."""

    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        self._lumis_depth = 0

    def compose_node(self, parent: Node | None, index: int) -> Node:
        if self.check_event(AliasEvent):  # type: ignore[no-untyped-call]
            raise ValueError("YAML aliases are not supported in Lumis configuration")
        self._lumis_depth += 1
        if self._lumis_depth > MAX_CONFIG_DEPTH:
            raise ValueError(f"YAML configuration exceeds maximum depth {MAX_CONFIG_DEPTH}")
        try:
            node = super().compose_node(parent, index)
            if node is None:
                raise ValueError("YAML configuration contains an empty node")
            return node
        finally:
            self._lumis_depth -= 1


def load_config(path: Path) -> LumisConfig:
    """Load a strict project and its legacy rule sets or structured rule documents."""
    document = ProjectDocument.model_validate(load_document_mapping(path))
    _warn_if_legacy(document.kind, document.api_version)
    config = _runtime_from_versioned(document)

    rules: list[DeterministicRule] = [*config.rules]
    structured_rules: list[DiagnosisRuleDocument] = [*config.structured_rules]
    for configured_path in config.rules_files:
        rule_path = resolve_project_path(path, configured_path)
        raw = load_document_mapping(rule_path)
        kind = raw.get("kind")
        api_version = raw.get("apiVersion")
        if api_version != config.source_api_version:
            raise ValueError(
                "Project and rule documents must use the same apiVersion; "
                "migrate the complete configuration collection together."
            )
        if kind == "DiagnosisRuleSet":
            rule_set = DiagnosisRuleSetDocument.model_validate(raw)
            _warn_if_legacy(rule_set.kind, rule_set.api_version)
            rules.extend(rule_set.spec.rules)
        elif kind == "DiagnosisRule":
            rule = DiagnosisRuleDocument.model_validate(raw)
            _warn_if_legacy(rule.kind, rule.api_version)
            structured_rules.append(rule)
        else:
            raise ValueError(f"Unsupported rule document kind {kind!r}: {rule_path}")
    if rules and structured_rules:
        raise ValueError(
            "A project cannot mix DiagnosisRuleSet and DiagnosisRule files; "
            "migrate the complete rule collection together."
        )
    return config.model_copy(update={"rules": rules, "structured_rules": structured_rules})


def load_rules_file(path: Path) -> list[DeterministicRule]:
    """Load one strict stable or compatibility diagnosis rule-set document."""
    document = DiagnosisRuleSetDocument.model_validate(load_document_mapping(path))
    _warn_if_legacy(document.kind, document.api_version)
    return document.spec.rules


def load_diagnosis_rule(path: Path) -> DiagnosisRuleDocument:
    """Load one strict stable or compatibility structured diagnosis-rule document."""
    document = DiagnosisRuleDocument.model_validate(load_document_mapping(path))
    _warn_if_legacy(document.kind, document.api_version)
    return document


def resolve_project_path(config_path: Path, configured_path: str) -> Path:
    """Resolve and normalize a configured project path relative to its YAML file."""
    path = Path(configured_path)
    return (path if path.is_absolute() else config_path.parent / path).resolve()


def project_json_schema() -> dict[str, Any]:
    """Return the checked configuration schema for tooling and editors."""
    return _stable_schema(ProjectDocument)


def rules_json_schema() -> dict[str, Any]:
    """Return the checked diagnosis rule-set schema for tooling and editors."""
    return _stable_schema(DiagnosisRuleSetDocument)


def diagnosis_rule_json_schema() -> dict[str, Any]:
    """Return the checked schema for a single structured diagnosis rule."""
    return _stable_schema(DiagnosisRuleDocument)


def legacy_project_json_schema() -> dict[str, Any]:
    """Return the frozen deprecated v1alpha1 project schema."""
    return _legacy_schema(ProjectDocument)


def legacy_rules_json_schema() -> dict[str, Any]:
    """Return the frozen deprecated v1alpha1 rule-set schema."""
    return _legacy_schema(DiagnosisRuleSetDocument)


def legacy_diagnosis_rule_json_schema() -> dict[str, Any]:
    """Return the frozen deprecated v1alpha1 structured-rule schema."""
    return _legacy_schema(DiagnosisRuleDocument)


def _runtime_from_versioned(document: ProjectDocument) -> LumisConfig:
    return LumisConfig(
        project=document.metadata.name,
        environment=document.spec.environment,
        memory=document.spec.memory,
        reports=document.spec.reports,
        incident_sources=document.spec.incident_sources,
        evidence_providers=document.spec.evidence_providers,
        rules_files=document.spec.rules.files,
        model=document.spec.model,
        source_api_version=document.api_version,
    )


def load_document_mapping(path: Path) -> dict[str, Any]:
    """Load one bounded YAML or JSON configuration mapping."""
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
        try:
            # BoundedSafeLoader is a SafeLoader subclass; Bandit cannot infer that relationship.
            return yaml.load(handle, Loader=BoundedSafeLoader) or {}  # nosec B506
        except RecursionError as error:
            raise ValueError("Configuration nesting exceeds the parser limit") from error


def _schema_for_version(model: type[Any], version: str) -> dict[str, Any]:
    schema = cast(dict[str, Any], model.model_json_schema(by_alias=True))
    api_version = schema["properties"]["apiVersion"]
    api_version.pop("enum", None)
    api_version["const"] = version
    return schema


def _stable_schema(model: type[Any]) -> dict[str, Any]:
    return _schema_for_version(model, PROJECT_API_VERSION)


def _legacy_schema(model: type[Any]) -> dict[str, Any]:
    return _schema_for_version(model, LEGACY_PROJECT_API_VERSION)


def _warn_if_legacy(kind: str, api_version: str) -> None:
    if api_version == LEGACY_PROJECT_API_VERSION:
        warnings.warn(
            f"{kind} uses deprecated {LEGACY_PROJECT_API_VERSION}; migrate to "
            f"{PROJECT_API_VERSION} with `lumis config migrate`. It is supported through "
            "the 1.x line and planned for removal in 2.0. Migration guide: "
            "https://github.com/soloshun/lumis-sdk/blob/main/docs/migrations/config-v1.md",
            LumisV1Alpha1DeprecationWarning,
            stacklevel=3,
        )


class LumisV1Alpha1DeprecationWarning(DeprecationWarning):
    """Warning emitted while reading a deprecated v1alpha1 configuration document."""
