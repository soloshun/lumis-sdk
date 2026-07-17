"""Deterministic migrations for versioned Lumis SDK configuration documents."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict

from lumis_sdk.domain.plugins import PLUGIN_KIND, PluginManifest
from lumis_sdk.domain.policy import (
    PLAYBOOK_KIND,
    POLICY_KIND,
    PlaybookDocument,
    PolicyDocument,
)
from lumis_sdk.domain.reports import DIAGNOSIS_REPORT_KIND, DiagnosisReportDocument

from .loader import load_document_mapping
from .models import (
    DIAGNOSIS_RULE_KIND,
    LEGACY_PROJECT_API_VERSION,
    PROJECT_API_VERSION,
    PROJECT_KIND,
    RULE_SET_KIND,
    DiagnosisRuleDocument,
    DiagnosisRuleSetDocument,
    ProjectDocument,
)

MigratableKind = Literal[
    "Project",
    "DiagnosisRuleSet",
    "DiagnosisRule",
    "DiagnosisReport",
    "PluginManifest",
    "Playbook",
    "RecoveryPolicy",
]


class ConfigMigrationResult(BaseModel):
    """Validated result of one configuration migration."""

    model_config = ConfigDict(frozen=True)

    kind: MigratableKind
    source_api_version: str
    target_api_version: str
    changed: bool
    document: dict[str, Any]


def migrate_config_document(raw: dict[str, Any]) -> ConfigMigrationResult:
    """Validate and migrate one supported document to the stable v1 marker."""
    kind = raw.get("kind")
    supported_kinds = {
        PROJECT_KIND,
        RULE_SET_KIND,
        DIAGNOSIS_RULE_KIND,
        DIAGNOSIS_REPORT_KIND,
        PLUGIN_KIND,
        PLAYBOOK_KIND,
        POLICY_KIND,
    }
    if kind not in supported_kinds:
        raise ValueError(f"Unsupported configuration document kind: {kind!r}")
    source_version = raw.get("apiVersion")
    if source_version not in {LEGACY_PROJECT_API_VERSION, PROJECT_API_VERSION}:
        raise ValueError(f"Unsupported configuration apiVersion: {source_version!r}")

    migrated = dict(raw)
    migrated["apiVersion"] = PROJECT_API_VERSION
    model = _model_for_kind(kind)
    validated = model.model_validate(migrated)
    canonical = validated.model_dump(
        mode="json", by_alias=True, exclude_none=True, exclude_unset=True
    )
    return ConfigMigrationResult(
        kind=kind,
        source_api_version=source_version,
        target_api_version=PROJECT_API_VERSION,
        changed=source_version != PROJECT_API_VERSION,
        document=canonical,
    )


def migrate_config_file(path: Path) -> ConfigMigrationResult:
    """Read a bounded YAML/JSON document and return its validated v1 representation."""
    return migrate_config_document(load_document_mapping(path))


def render_migrated_yaml(result: ConfigMigrationResult) -> str:
    """Render a migration result with deterministic key ordering and no YAML aliases."""
    return yaml.safe_dump(result.document, sort_keys=False, allow_unicode=True)


def _model_for_kind(
    kind: MigratableKind,
) -> type[BaseModel]:
    if kind == PROJECT_KIND:
        return ProjectDocument
    if kind == RULE_SET_KIND:
        return DiagnosisRuleSetDocument
    if kind == DIAGNOSIS_RULE_KIND:
        return DiagnosisRuleDocument
    if kind == DIAGNOSIS_REPORT_KIND:
        return DiagnosisReportDocument
    if kind == PLUGIN_KIND:
        return PluginManifest
    if kind == PLAYBOOK_KIND:
        return PlaybookDocument
    return PolicyDocument
