"""Tests for the OpenARIA command-line interface."""

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
