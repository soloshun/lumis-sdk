"""Tests for strict versioned configuration and schema generation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from lumis_sdk.config import (
    MAX_CONFIG_BYTES,
    diagnosis_rule_json_schema,
    load_config,
    project_json_schema,
    rules_json_schema,
)


def test_versioned_project_and_rule_set_load_strictly(tmp_path: Path) -> None:
    """A v1alpha1 project resolves its external versioned rules."""
    (tmp_path / "rules.yml").write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRuleSet
metadata:
  name: fixture-rules
spec:
  rules:
    - id: fixture-rule
      name: fixture-rule
      version: "2"
      priority: 100
      all_contains: ["SIGNATURE"]
      classification: fixture_failure
      severity: low
      summary: A fixture failed.
      root_cause_hypothesis: The fixture signature matched.
      confidence: 0.7
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: fixture-project
spec:
  rules:
    files: [rules.yml]
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.source_api_version == "lumis.dev/v1alpha1"
    assert config.rules[0].stable_id == "fixture-rule"
    assert config.rules[0].version == "2"
    assert config.rules[0].priority == 100


def test_unknown_versioned_field_is_rejected(tmp_path: Path) -> None:
    """Misspelled fields never disappear silently."""
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: fixture-project
spec:
  enviroment: production
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="enviroment"):
        load_config(config_path)


def test_project_schema_rejects_additional_properties() -> None:
    """Generated editor/tooling schema mirrors strict validation."""
    schema = project_json_schema()

    assert schema["additionalProperties"] is False
    assert schema["properties"]["apiVersion"]["const"] == "lumis.dev/v1alpha1"

    rules_schema = rules_json_schema()
    assert rules_schema["additionalProperties"] is False
    rule_definition = rules_schema["$defs"]["DeterministicRule"]
    assert "id" in rule_definition["required"]


def test_project_accepts_secret_referenced_postgres_memory(tmp_path: Path) -> None:
    """PostgreSQL configuration contains only a secret reference and bounded settings."""
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: shared-memory
spec:
  memory:
    provider: postgres
    connectionUrlEnv: LUMIS_MEMORY_DATABASE_URL
    schema: adopter_memory
    connectTimeoutSeconds: 7
    maxSearchCandidates: 500
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.memory.provider == "postgres"
    assert config.memory.connection_url_env == "LUMIS_MEMORY_DATABASE_URL"
    assert config.memory.schema_name == "adopter_memory"
    assert "postgresql://" not in config_path.read_text(encoding="utf-8")


def test_oversized_configuration_is_rejected(tmp_path: Path) -> None:
    """Configuration loading has a deterministic size boundary."""
    config_path = tmp_path / "lumis.yml"
    config_path.write_bytes(b"x" * (MAX_CONFIG_BYTES + 1))

    with pytest.raises(ValueError, match="exceeds"):
        load_config(config_path)


def test_project_can_load_single_structured_rule_documents(tmp_path: Path) -> None:
    """Project rule paths may select the v0.2 single-document contract."""
    (tmp_path / "rule.yml").write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRule
metadata:
  name: timeout
  version: "3"
spec:
  priority: 50
  match:
    all:
      - field: duration.seconds
        greaterThan: 300
  diagnosis:
    classification: orchestration_failure
    summary: A task exceeded its expected duration.
    hypothesis: The task may be stuck.
    confidence: 0.7
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: fixture-project
spec:
  rules:
    files: [rule.yml]
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.rules == []
    assert config.structured_rules[0].stable_id == "timeout"
    assert config.structured_rules[0].metadata.version == "3"
    schema = diagnosis_rule_json_schema()
    assert schema["properties"]["kind"]["const"] == "DiagnosisRule"
    assert schema["additionalProperties"] is False


def test_project_rejects_mixed_legacy_and_structured_rule_collections(tmp_path: Path) -> None:
    """Cross-engine ordering stays explicit during the all_contains migration."""
    (tmp_path / "legacy.yml").write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRuleSet
metadata:
  name: legacy
spec:
  rules:
    - id: legacy
      name: legacy
      all_contains: [SIGNATURE]
      classification: legacy
      severity: medium
      summary: Legacy.
      root_cause_hypothesis: Legacy.
      confidence: 0.5
""",
        encoding="utf-8",
    )
    (tmp_path / "structured.yml").write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRule
metadata:
  name: structured
spec:
  match:
    all:
      - field: log.text
        contains: SIGNATURE
  diagnosis:
    classification: structured
    summary: Structured.
    hypothesis: Structured.
    confidence: 0.5
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: fixture-project
spec:
  rules:
    files: [legacy.yml, structured.yml]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot mix"):
        load_config(config_path)
