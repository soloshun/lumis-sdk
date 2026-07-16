"""Tests for the Lumis SDK command-line interface."""

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from lumis_sdk.cli import app

runner = CliRunner()


def _project_config(tmp_path: Path) -> Path:
    (tmp_path / "rules.yml").write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRuleSet
metadata:
  name: fixture-rules
spec:
  rules:
    - id: fixture-rule
      name: fixture-rule
      all_contains: ["INCIDENT_SIGNATURE"]
      classification: configured_failure
      severity: medium
      summary: The fixture signature appeared.
      root_cause_hypothesis: The configured rule matched.
      confidence: 0.6
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
  memory:
    path: incidents.db
  reports:
    outputDir: reports
  rules:
    files: [rules.yml]
""",
        encoding="utf-8",
    )
    return config_path


def test_help_describes_lumis_sdk() -> None:
    """The base command exposes a usable help screen."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Lumis SDK" in result.output
    assert "structured incident reports" in result.output


def test_version_is_available() -> None:
    """The package version can be inspected without extra dependencies."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == "0.0.2"


def test_diagnose_writes_an_evidence_grounded_report(tmp_path: Path) -> None:
    """A configured project rule produces a local Markdown report."""
    config_path = _project_config(tmp_path)
    log_path = tmp_path / "failure.log"
    log_path.write_text("ERROR INCIDENT_SIGNATURE", encoding="utf-8")
    output_path = tmp_path / "incident-report.md"

    result = runner.invoke(
        app,
        [
            "diagnose",
            "--config",
            str(config_path),
            "--log",
            str(log_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()

    report = output_path.read_text(encoding="utf-8")
    assert "Classification: configured_failure" in report
    assert "INCIDENT_SIGNATURE" in report
    assert "Likely Root Cause (Hypothesis)" in report
    assert "not a confirmed cause" in report
    assert "has not executed a remediation action" in report


def test_cli_can_retrieve_resolve_and_search_a_saved_incident(tmp_path: Path) -> None:
    """The memory commands work against an isolated local SQLite database."""
    config_path = _project_config(tmp_path)
    log_path = tmp_path / "failure.log"
    log_path.write_text("ERROR INCIDENT_SIGNATURE", encoding="utf-8")
    output_path = tmp_path / "incident-report.md"

    diagnosis_result = runner.invoke(
        app,
        [
            "diagnose",
            "--config",
            str(config_path),
            "--log",
            str(log_path),
            "--output",
            str(output_path),
        ],
    )

    incident_id_match = re.search(r"Incident ID: (?P<id>[\w-]+)", diagnosis_result.output)
    assert diagnosis_result.exit_code == 0
    assert incident_id_match is not None
    incident_id = incident_id_match.group("id")

    search_result = runner.invoke(
        app,
        ["memory", "search", "INCIDENT_SIGNATURE", "--config", str(config_path)],
    )
    assert search_result.exit_code == 0
    assert incident_id in search_result.output
    assert "score=1" in search_result.output

    resolve_result = runner.invoke(
        app,
        [
            "resolve",
            incident_id,
            "--resolution",
            "Updated the source mapping.",
            "--config",
            str(config_path),
        ],
    )
    assert resolve_result.exit_code == 0

    report_result = runner.invoke(
        app,
        ["report", incident_id, "--config", str(config_path)],
    )
    assert report_result.exit_code == 0
    assert "## Final Resolution" in report_result.output
    assert "Updated the source mapping." in report_result.output


def test_init_doctor_and_rule_validation_form_a_local_project(tmp_path: Path) -> None:
    """A generated project validates without credentials or network access."""
    init_result = runner.invoke(app, ["init", "--destination", str(tmp_path)])

    assert init_result.exit_code == 0
    config_path = tmp_path / "lumis.yml"
    assert config_path.exists()
    assert (tmp_path / "rules.yml").exists()

    doctor_result = runner.invoke(app, ["doctor", "--config", str(config_path)])
    assert doctor_result.exit_code == 0
    assert "api version: lumis.dev/v1alpha1" in doctor_result.output
    assert "model assistance: disabled" in doctor_result.output

    rules_result = runner.invoke(app, ["rules", "validate", "--config", str(config_path), "--json"])
    assert rules_result.exit_code == 0
    assert json.loads(rules_result.output) == {"valid": True, "rules": []}


def test_rules_test_emits_machine_readable_compound_explanation(tmp_path: Path) -> None:
    """A single portable DiagnosisRule can be validated and evaluated from the CLI."""
    rule_path = tmp_path / "rule.yml"
    rule_path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRule
metadata:
  name: schema-change
  version: "2"
spec:
  priority: 100
  match:
    all:
      - field: log.text
        contains: KeyError
      - field: schema.diff.removed_count
        greaterThan: 0
  diagnosis:
    classification: schema_change
    severity: high
    summary: A required field was removed.
    hypothesis: The upstream schema changed.
    confidence: 0.8
  evidence:
    required: [schema_diff]
""",
        encoding="utf-8",
    )
    input_path = tmp_path / "incident.json"
    input_path.write_text(
        json.dumps(
            {
                "fields": {
                    "log": {"text": "ERROR KeyError: customer_id"},
                    "schema": {"diff": {"removed_count": 1}},
                },
                "evidence": [
                    {
                        "id": "schema-1",
                        "source": "schema-registry",
                        "detail": "customer_id was removed",
                        "confidence": 1.0,
                        "kind": "schema_diff",
                        "reference": "schema://orders/diff",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["rules", "test", "--rule", str(rule_path), "--input", str(input_path)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["matched"] is True
    assert output["winner"] == "schema-change"
    assert output["candidates"][0]["evidenceReferences"] == ["schema://orders/diff"]


def test_diagnose_uses_structured_log_rule_from_project_config(tmp_path: Path) -> None:
    """The local diagnose flow can consume a single structured rule document."""
    (tmp_path / "rule.yml").write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRule
metadata:
  name: structured-signature
spec:
  match:
    all:
      - field: log.text
        contains: INCIDENT_SIGNATURE
  diagnosis:
    classification: structured_failure
    summary: The structured signature appeared.
    hypothesis: The configured structured rule matched.
    confidence: 0.7
  evidence:
    required: [log_window]
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "lumis.yml"
    config_path.write_text(
        """apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: structured-project
spec:
  memory:
    path: incidents.db
  reports:
    outputDir: reports
  rules:
    files: [rule.yml]
""",
        encoding="utf-8",
    )
    log_path = tmp_path / "failure.log"
    log_path.write_text("ERROR INCIDENT_SIGNATURE", encoding="utf-8")
    output_path = tmp_path / "report.md"

    result = runner.invoke(
        app,
        [
            "diagnose",
            "--config",
            str(config_path),
            "--log",
            str(log_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "Classification: structured_failure" in output_path.read_text(encoding="utf-8")
