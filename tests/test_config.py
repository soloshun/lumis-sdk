"""Tests for project-owned YAML/JSON configuration and external rules."""

from pathlib import Path

from openaria.config import load_config


def test_yaml_rules_file_is_loaded_relative_to_project_config(tmp_path: Path) -> None:
    """A project may keep its growing rule library outside its main YAML file."""
    (tmp_path / "rules.yml").write_text(
        """rules:
  - name: external-rule
    all_contains: ["EXTERNAL_SIGNATURE"]
    classification: external_failure
    severity: low
    summary: An external rule matched.
    root_cause_hypothesis: The fixture rule matched.
    confidence: 0.4
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "openaria.yml"
    config_path.write_text(
        """project: fixture-project
telemetry:
  log: logs/failure.log
rules_file: rules.yml
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.telemetry.log == "logs/failure.log"
    assert len(config.rules) == 1
    assert config.rules[0].classification == "external_failure"


def test_json_rules_file_is_supported(tmp_path: Path) -> None:
    """JSON rule libraries work for projects that prefer JSON tooling."""
    (tmp_path / "rules.json").write_text(
        '[{"name":"json-rule","all_contains":["JSON_SIGNATURE"],'
        '"classification":"json_failure","severity":"high",'
        '"summary":"A JSON rule matched.",'
        '"root_cause_hypothesis":"The JSON fixture matched.","confidence":0.8}]',
        encoding="utf-8",
    )
    config_path = tmp_path / "openaria.yml"
    config_path.write_text("project: fixture\nrules_file: rules.json\n", encoding="utf-8")

    assert load_config(config_path).rules[0].classification == "json_failure"
