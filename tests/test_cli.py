"""Tests for the OpenARIA command-line interface."""

import re
from pathlib import Path

from typer.testing import CliRunner

from openaria.cli import app

runner = CliRunner()


def test_help_describes_openaria() -> None:
    """The base command exposes a usable help screen."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "OpenARIA" in result.output
    assert "structured incident reports" in result.output


def test_version_is_available() -> None:
    """The package version can be inspected without extra dependencies."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == "0.1.0"


def test_diagnose_writes_an_evidence_grounded_report(tmp_path: Path) -> None:
    """The first synthetic failure produces a local Markdown report."""
    log_path = Path("examples/simple-log-diagnosis/failure.log")
    output_path = tmp_path / "incident-report.md"

    result = runner.invoke(
        app,
        ["diagnose", "--log", str(log_path), "--output", str(output_path)],
    )

    assert result.exit_code == 0
    assert output_path.exists()

    report = output_path.read_text(encoding="utf-8")
    assert "Classification: schema_change" in report
    assert "KeyError: 'Close'" in report
    assert "Likely Root Cause (Hypothesis)" in report
    assert "not a confirmed cause" in report
    assert "has not executed a remediation action" in report


def test_cli_can_retrieve_resolve_and_search_a_saved_incident(tmp_path: Path) -> None:
    """The memory commands work against an isolated local SQLite database."""
    log_path = Path("examples/simple-log-diagnosis/failure.log")
    output_path = tmp_path / "incident-report.md"
    memory_path = tmp_path / "incidents.db"

    diagnosis_result = runner.invoke(
        app,
        [
            "diagnose",
            "--log",
            str(log_path),
            "--output",
            str(output_path),
            "--memory-path",
            str(memory_path),
        ],
    )

    incident_id_match = re.search(r"Incident ID: (?P<id>[\w-]+)", diagnosis_result.output)
    assert diagnosis_result.exit_code == 0
    assert incident_id_match is not None
    incident_id = incident_id_match.group("id")

    search_result = runner.invoke(
        app,
        ["memory", "search", "KeyError Close", "--memory-path", str(memory_path)],
    )
    assert search_result.exit_code == 0
    assert incident_id in search_result.output
    assert "score=2" in search_result.output

    resolve_result = runner.invoke(
        app,
        [
            "resolve",
            incident_id,
            "--resolution",
            "Updated the source mapping.",
            "--memory-path",
            str(memory_path),
        ],
    )
    assert resolve_result.exit_code == 0

    report_result = runner.invoke(
        app,
        ["report", incident_id, "--memory-path", str(memory_path)],
    )
    assert report_result.exit_code == 0
    assert "## Final Resolution" in report_result.output
    assert "Updated the source mapping." in report_result.output
