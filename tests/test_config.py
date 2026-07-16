"""Tests for strict project-owned YAML/JSON configuration."""

from pathlib import Path

from lumis_sdk.config import load_config


def test_yaml_rule_set_is_loaded_relative_to_project_config(tmp_path: Path) -> None:
    (tmp_path / "rules.yml").write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRuleSet
metadata:
  name: fixture-rules
spec:
  rules:
    - id: external-rule
      name: external-rule
      all_contains: ["EXTERNAL_SIGNATURE"]
      classification: external_failure
      severity: low
      summary: An external rule matched.
      root_cause_hypothesis: The fixture rule matched.
      confidence: 0.4
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
  incidentSources:
    - provider: local-log
      path: logs/failure.log
  evidenceProviders:
    - provider: local-json
      path: evidence/context.json
      kinds: [schema_diff]
      maxItems: 5
      maxTotalCharacters: 5000
      maxItemCharacters: 1000
      timeoutSeconds: 2
  rules:
    files: [rules.yml]
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.incident_sources[0].path == "logs/failure.log"
    assert config.evidence_providers[0].provider == "local-json"
    assert config.evidence_providers[0].max_items == 5
    assert config.rules[0].classification == "external_failure"


def test_json_rule_set_is_supported(tmp_path: Path) -> None:
    (tmp_path / "rules.json").write_text(
        '{"apiVersion":"lumis.dev/v1alpha1","kind":"DiagnosisRuleSet",'
        '"metadata":{"name":"json-rules"},"spec":{"rules":[{'
        '"id":"json-rule","name":"json-rule","all_contains":["JSON_SIGNATURE"],'
        '"classification":"json_failure","severity":"high",'
        '"summary":"A JSON rule matched.",'
        '"root_cause_hypothesis":"The JSON fixture matched.","confidence":0.8}]}}',
        encoding="utf-8",
    )
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: fixture
spec:
  rules:
    files: [rules.json]
""",
        encoding="utf-8",
    )

    assert load_config(config_path).rules[0].classification == "json_failure"
