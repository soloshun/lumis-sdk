"""Tests for strict versioned configuration and schema generation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from lumis_sdk.config import (
    MAX_CONFIG_BYTES,
    MAX_CONFIG_DEPTH,
    LumisV1Alpha1DeprecationWarning,
    diagnosis_rule_json_schema,
    legacy_project_json_schema,
    load_config,
    migrate_config_document,
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

    with pytest.warns(LumisV1Alpha1DeprecationWarning):
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
    assert schema["properties"]["apiVersion"]["const"] == "lumis.dev/v1"
    assert legacy_project_json_schema()["properties"]["apiVersion"]["const"] == "lumis.dev/v1alpha1"

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


def test_project_accepts_allowlisted_http_json_evidence(tmp_path: Path) -> None:
    """The optional HTTP connector is strict, HTTPS-only, and secret-referenced."""
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: connector-project
spec:
  evidenceProviders:
    - provider: http-json
      url: https://evidence.example.test/v1/evidence
      allowedOrigins: [https://evidence.example.test]
      tokenEnv: LUMIS_EVIDENCE_TOKEN
      kinds: [schema_diff]
      maxResponseBytes: 50000
      timeoutSeconds: 3
      retries: 1
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    provider = config.evidence_providers[0]
    assert provider.provider == "http-json"
    assert provider.token_env == "LUMIS_EVIDENCE_TOKEN"
    assert provider.allowed_origins == ["https://evidence.example.test"]


@pytest.mark.parametrize(
    "url",
    [
        "http://evidence.example.test/v1/evidence",
        "https://user:password@evidence.example.test/v1/evidence",
        "https://other.example.test/v1/evidence",
    ],
)
def test_http_json_evidence_rejects_unsafe_destinations(tmp_path: Path, url: str) -> None:
    """Non-HTTPS, credential-bearing, and non-allowlisted destinations fail validation."""
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        f"""apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: unsafe-connector
spec:
  evidenceProviders:
    - provider: http-json
      url: {url}
      allowedOrigins: [https://evidence.example.test]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_config(config_path)


def test_oversized_configuration_is_rejected(tmp_path: Path) -> None:
    """Configuration loading has a deterministic size boundary."""
    config_path = tmp_path / "lumis.yml"
    config_path.write_bytes(b"x" * (MAX_CONFIG_BYTES + 1))

    with pytest.raises(ValueError, match="exceeds"):
        load_config(config_path)


def test_yaml_aliases_are_rejected_before_construction(tmp_path: Path) -> None:
    """Configuration cannot use aliases to amplify or obscure reviewed values."""
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1
kind: Project
metadata:
  name: alias-project
spec:
  memory: &shared
    provider: sqlite
  reports: *shared
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="aliases are not supported"):
        load_config(config_path)


def test_excessive_yaml_depth_is_rejected(tmp_path: Path) -> None:
    """Deeply nested YAML fails at a deterministic parser boundary."""
    nested = "value: leaf\n"
    for _ in range(MAX_CONFIG_DEPTH + 1):
        nested = "level:\n" + "".join(f"  {line}\n" for line in nested.splitlines())
    config_path = tmp_path / "deep.yml"
    config_path.write_text(nested, encoding="utf-8")

    with pytest.raises(ValueError, match="maximum depth"):
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


def test_stable_v1_project_and_rule_documents_load_without_deprecation(tmp_path: Path) -> None:
    """Stable documents form the default contract and load as one versioned collection."""
    (tmp_path / "rules.yml").write_text(
        """apiVersion: lumis.dev/v1
kind: DiagnosisRuleSet
metadata:
  name: stable-rules
spec:
  rules: []
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1
kind: Project
metadata:
  name: stable-project
spec:
  rules:
    files: [rules.yml]
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.source_api_version == "lumis.dev/v1"


def test_project_rejects_mixed_api_versions(tmp_path: Path) -> None:
    """A project cannot silently combine stable and deprecated rule contracts."""
    (tmp_path / "rules.yml").write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRuleSet
metadata:
  name: old-rules
spec:
  rules: []
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1
kind: Project
metadata:
  name: stable-project
spec:
  rules:
    files: [rules.yml]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="same apiVersion"):
        load_config(config_path)


def test_v1alpha1_migration_is_validated_idempotent_and_shape_preserving() -> None:
    """Migration changes only the marker and can safely be repeated."""
    raw = {
        "apiVersion": "lumis.dev/v1alpha1",
        "kind": "Project",
        "metadata": {"name": "migration-fixture"},
        "spec": {"environment": "staging"},
    }

    first = migrate_config_document(raw)
    second = migrate_config_document(first.document)

    assert first.changed is True
    assert first.document == {
        "apiVersion": "lumis.dev/v1",
        "kind": "Project",
        "metadata": {"name": "migration-fixture"},
        "spec": {"environment": "staging"},
    }
    assert second.changed is False
    assert second.document == first.document


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        (
            "DiagnosisRuleSet",
            {"metadata": {"name": "rules"}, "spec": {"rules": []}},
        ),
        (
            "DiagnosisRule",
            {
                "metadata": {"name": "timeout"},
                "spec": {
                    "match": {"all": [{"field": "log.text", "contains": "timeout"}]},
                    "diagnosis": {
                        "classification": "timeout",
                        "summary": "A timeout occurred.",
                        "hypothesis": "A dependency may be unavailable.",
                        "confidence": 0.5,
                    },
                },
            },
        ),
        (
            "PluginManifest",
            {
                "metadata": {"name": "fixture-plugin", "version": "1.0.0"},
                "spec": {
                    "entryPoint": "fixture:create_plugin",
                    "capabilities": ["evidence_provider"],
                    "supportStatus": "community",
                    "sdk": {"minimum": "0.0.8", "maximumExclusive": "2.0.0"},
                    "summary": "A fixture plugin.",
                },
            },
        ),
        (
            "Playbook",
            {
                "metadata": {"name": "restart", "version": "1"},
                "actions": [
                    {"name": "restart_task", "summary": "Restart one task.", "risk": "medium"}
                ],
            },
        ),
        (
            "RecoveryPolicy",
            {
                "metadata": {"name": "safe-defaults", "version": "1"},
                "default_deny": True,
                "rules": [],
            },
        ),
    ],
)
def test_every_released_versioned_configuration_shape_migrates(
    kind: str, payload: dict[str, object]
) -> None:
    """Each released alpha configuration envelope has a stable v1 migration."""
    result = migrate_config_document({"apiVersion": "lumis.dev/v1alpha1", "kind": kind, **payload})

    assert result.kind == kind
    assert result.document["apiVersion"] == "lumis.dev/v1"
