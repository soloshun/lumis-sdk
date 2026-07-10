"""Command-line interface for OpenARIA."""

from pathlib import Path

import typer

from openaria import __version__
from openaria.config import OpenARIAConfig, load_config, resolve_project_path
from openaria.incidents import incident_from_log
from openaria.llm import diagnose_with_optional_model
from openaria.memory import IncidentNotFoundError, SQLiteIncidentStore, search_incidents
from openaria.reports import append_resolution, render_markdown_report

app = typer.Typer(
    name="openaria",
    help="Turn pipeline failures into structured incident reports.",
    no_args_is_help=True,
)
memory_app = typer.Typer(help="Search local OpenARIA incident memory.")
app.add_typer(memory_app, name="memory")

DEFAULT_CONFIG_PATH = Path("openaria.yml")


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
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the project OpenARIA YAML configuration.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional override for the configured Markdown report path.",
    ),
) -> None:
    """Diagnose a local log using the project's configured deterministic rules."""
    project_config = load_config(config)
    log_text = log.read_text(encoding="utf-8")
    incident = incident_from_log(log_text, str(log), project_config.project)
    diagnosis = diagnose_with_optional_model(log_text, rules=project_config.rules)
    report = render_markdown_report(incident, diagnosis)

    report_path = output or resolve_project_path(
        config, f"{project_config.reports.output_dir}/incident-report.md"
    )
    memory_path = resolve_project_path(config, project_config.memory.path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    stored = SQLiteIncidentStore(memory_path).save(incident, diagnosis, report, report_path)
    typer.echo(f"Incident report written to {report_path}")
    typer.echo(f"Incident ID: {stored.id}")


@app.command()
def report(
    incident_id: str,
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        exists=True,
        help="Path to the project OpenARIA YAML configuration.",
    ),
) -> None:
    """Print a stored incident report, including its final resolution if present."""
    try:
        stored = SQLiteIncidentStore(_memory_path(config)).get(incident_id)
    except IncidentNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(append_resolution(stored.report_markdown, stored.resolution))


@app.command()
def resolve(
    incident_id: str,
    resolution: str = typer.Option(..., "--resolution", help="Human-confirmed final resolution."),
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        exists=True,
        help="Path to the project OpenARIA YAML configuration.",
    ),
) -> None:
    """Store a human-confirmed resolution for an incident."""
    try:
        SQLiteIncidentStore(_memory_path(config)).set_resolution(incident_id, resolution)
    except IncidentNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Resolution saved for incident {incident_id}")


@memory_app.command("search")
def memory_search(
    query: str,
    config: Path = typer.Option(
        DEFAULT_CONFIG_PATH,
        "--config",
        exists=True,
        help="Path to the project OpenARIA YAML configuration.",
    ),
) -> None:
    """Find similar incidents using transparent local keyword matching."""
    results = search_incidents(SQLiteIncidentStore(_memory_path(config)).list_all(), query)
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


def _memory_path(config_path: Path) -> Path:
    """Resolve the local incident-memory path from a project configuration."""
    project_config: OpenARIAConfig = load_config(config_path)
    return resolve_project_path(config_path, project_config.memory.path)
