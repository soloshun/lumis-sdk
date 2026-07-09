"""Tests for the Sprint 0 command-line interface."""

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
