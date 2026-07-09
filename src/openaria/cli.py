"""Command-line interface for OpenARIA."""

from pathlib import Path

import typer

from openaria import __version__
from openaria.incidents import incident_from_log
from openaria.reports import render_markdown_report
from openaria.triage import diagnose_log

app = typer.Typer(
    name="openaria",
    help="Turn pipeline failures into structured incident reports.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print the package version when requested."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def openaria(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the OpenARIA version and exit.",
    ),
) -> None:
    """OpenARIA command-line interface."""


@app.command()
def diagnose(
    log: Path = typer.Option(
        ...,
        "--log",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to a local pipeline-failure log.",
    ),
    output: Path = typer.Option(
        Path(".openaria/reports/incident-report.md"),
        "--output",
        help="Path where the Markdown incident report will be written.",
    ),
) -> None:
    """Diagnose a local log with deterministic, evidence-only rules."""
    log_text = log.read_text(encoding="utf-8")
    incident = incident_from_log(log_text, str(log))
    diagnosis = diagnose_log(log_text)
    report = render_markdown_report(incident, diagnosis)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    typer.echo(f"Incident report written to {output}")


def main() -> None:
    """Run the OpenARIA CLI."""
    app()
