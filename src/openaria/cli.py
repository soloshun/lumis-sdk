"""Command-line interface for OpenARIA."""

from pathlib import Path

import typer

from openaria import __version__
from openaria.incidents import incident_from_log
from openaria.memory import IncidentNotFoundError, SQLiteIncidentStore, search_incidents
from openaria.reports import append_resolution, render_markdown_report
from openaria.triage import diagnose_log

app = typer.Typer(
    name="openaria",
    help="Turn pipeline failures into structured incident reports.",
    no_args_is_help=True,
)
memory_app = typer.Typer(help="Search local OpenARIA incident memory.")
app.add_typer(memory_app, name="memory")

DEFAULT_MEMORY_PATH = Path(".openaria/incidents.db")


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
    memory_path: Path = typer.Option(
        DEFAULT_MEMORY_PATH,
        "--memory-path",
        help="Path to the local SQLite incident-memory database.",
    ),
) -> None:
    """Diagnose a local log with deterministic, evidence-only rules."""
    log_text = log.read_text(encoding="utf-8")
    incident = incident_from_log(log_text, str(log))
    diagnosis = diagnose_log(log_text)
    report = render_markdown_report(incident, diagnosis)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    stored = SQLiteIncidentStore(memory_path).save(incident, diagnosis, report, output)
    typer.echo(f"Incident report written to {output}")
    typer.echo(f"Incident ID: {stored.id}")


@app.command()
def report(
    incident_id: str,
    memory_path: Path = typer.Option(
        DEFAULT_MEMORY_PATH,
        "--memory-path",
        help="Path to the local SQLite incident-memory database.",
    ),
) -> None:
    """Print a stored incident report, including its final resolution if present."""
    try:
        stored = SQLiteIncidentStore(memory_path).get(incident_id)
    except IncidentNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(append_resolution(stored.report_markdown, stored.resolution))


@app.command()
def resolve(
    incident_id: str,
    resolution: str = typer.Option(..., "--resolution", help="Human-confirmed final resolution."),
    memory_path: Path = typer.Option(
        DEFAULT_MEMORY_PATH,
        "--memory-path",
        help="Path to the local SQLite incident-memory database.",
    ),
) -> None:
    """Store a human-confirmed resolution for an incident."""
    try:
        SQLiteIncidentStore(memory_path).set_resolution(incident_id, resolution)
    except IncidentNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Resolution saved for incident {incident_id}")


@memory_app.command("search")
def memory_search(
    query: str,
    memory_path: Path = typer.Option(
        DEFAULT_MEMORY_PATH,
        "--memory-path",
        help="Path to the local SQLite incident-memory database.",
    ),
) -> None:
    """Find similar incidents using transparent local keyword matching."""
    results = search_incidents(SQLiteIncidentStore(memory_path).list_all(), query)
    if not results:
        typer.echo("No matching incidents found.")
        return

    typer.echo("Matching incidents (keyword score):")
    for result in results:
        stored = result.incident
        pipeline_name = stored.incident.pipeline_name or "not provided"
        resolution_status = "resolved" if stored.resolution else "unresolved"
        typer.echo(
            "- "
            f"{stored.id} | score={result.score} | {stored.diagnosis.triage.classification} | "
            f"{pipeline_name} | {resolution_status}"
        )


def main() -> None:
    """Run the OpenARIA CLI."""
    app()
