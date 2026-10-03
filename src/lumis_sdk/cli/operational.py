"""CLI adapters: explicit local reads, opt-in discovery, opt-in paid model calls."""

import asyncio
import importlib.util
import os
import shutil
from pathlib import Path

import typer
from pydantic import TypeAdapter

from lumis_sdk.core import Evidence, GraphSnapshot, Incident
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.runtime import DiscoveryError, InvestigationStore, YamlProject
from lumis_sdk.runtime.discovery import discover_project
from lumis_sdk.runtime.documents import json_document
from lumis_sdk.runtime.project import load_project, read_document


def init(
    directory: Path = typer.Option(Path("."), "--directory", help="New local workspace directory."),
) -> None:
    """Create a minimal offline project, incident and observations; refuse existing files."""
    from lumis_sdk.runtime.scaffold import starter_documents

    files = starter_documents()
    created: list[Path] = []
    try:
        directory.mkdir(parents=True, exist_ok=True)
        if any((directory / name).exists() for name in files):
            raise typer.BadParameter("Scaffold files already exist; choose a new directory.")
        for name, content in files.items():
            path = directory / name
            with path.open("x", encoding="utf-8") as stream:
                created.append(path)
                stream.write(content)
    except OSError as error:
        for path in created:
            path.unlink(missing_ok=True)
        raise typer.BadParameter(
            "Unable to create scaffold; existing files were not changed."
        ) from error
    typer.echo(
        f"Created offline project in {directory}. Run lumis doctor --project {directory}/lumis.yaml"
    )


def doctor(
    project: Path = typer.Option(Path("lumis.yaml"), "--project", exists=True, readable=True),
) -> None:
    """Validate local configuration and optional tool availability without making network calls."""
    try:
        config = load_project(project)
    except Exception as error:
        raise typer.BadParameter(
            "Invalid project; check the YAML guide and generated schema."
        ) from error
    warnings: list[str] = []
    if config.sources.kubernetes.enabled and not shutil.which("kubectl"):
        warnings.append("Kubernetes discovery requires kubectl on PATH.")
    if (config.sources.prometheus.enabled or config.models) and not importlib.util.find_spec(
        "httpx"
    ):
        warnings.append("Optional HTTP features require lumis-sdk[http].")
    if config.models and not os.environ.get(config.models.credential_env):
        warnings.append(
            "Configured model credential is absent; offline investigation remains available."
        )
    if config.sources.opentelemetry.enabled:
        assert config.sources.opentelemetry.export_file is not None
        export = Path(config.sources.opentelemetry.export_file)
        if not (export if export.is_absolute() else project.parent / export).is_file():
            warnings.append("Configured OTLP JSON export is absent.")
    if config.sources.topology.enabled:
        assert config.sources.topology.file_path is not None
        snapshot = Path(config.sources.topology.file_path)
        if not (snapshot if snapshot.is_absolute() else project.parent / snapshot).is_file():
            warnings.append("Configured topology JSON snapshot is absent.")
    typer.echo(
        json_document(
            {
                "valid": True,
                "project": config.project.name,
                "environment": config.project.environment,
                "mode": "read_only",
                "network_checked": False,
                "warnings": warnings,
            }
        ).rstrip()
    )


def discover(
    project: Path = typer.Option(Path("lumis.yaml"), "--project", exists=True, readable=True),
    report: bool = typer.Option(False, "--report", help="Include per-source readiness statuses."),
) -> None:
    """Merge declared topology with all enabled, bounded read-only sources."""
    try:
        config = load_project(project)
        result = asyncio.run(discover_project(config, project.parent))
    except DiscoveryError as error:
        if report:
            typer.echo(json_document(error.report.model_dump(mode="json")).rstrip())
            raise typer.Exit(1) from error
        raise typer.BadParameter(
            "Discovery incomplete; use --report to inspect statuses."
        ) from error
    except Exception as error:
        raise typer.BadParameter(
            "Discovery failed; check configuration, scope, RBAC and bounds."
        ) from error
    typer.echo(
        json_document(result.model_dump(mode="json")).rstrip()
        if report
        else result.graph.model_dump_json(indent=2)
    )


def graph(
    project: Path = typer.Option(Path("lumis.yaml"), "--project", exists=True, readable=True),
    entity: str | None = typer.Option(
        None, "--entity", help="Scope around one canonical entity ID."
    ),
    hops: int = typer.Option(3, "--hops", min=0, max=10),
    format: str = typer.Option(
        "json", "--format", help="json or dot; DOT needs no plotting extras."
    ),
) -> None:
    """Discover and inspect the operational graph, optionally bounded around an entity."""
    if format not in {"json", "dot"}:
        raise typer.BadParameter("format must be json or dot")
    try:
        prepared = asyncio.run(YamlProject.from_file(project).prepare())
        selected = prepared.graph
        if entity is not None:
            selected = OperationalGraph(
                selected.dependencies_within(
                    entity, hops=hops, max_entities=prepared.config.budget.max_entities
                )
            )
    except Exception as error:
        raise typer.BadParameter(
            "Graph not ready; check discovery and canonical references."
        ) from error
    typer.echo(
        selected.to_dot() if format == "dot" else selected.snapshot().model_dump_json(indent=2)
    )


def investigate(
    project: Path = typer.Option(Path("lumis.yaml"), "--project", exists=True, readable=True),
    incident: Path = typer.Option(..., "--incident", exists=True, readable=True),
    observations: Path | None = typer.Option(None, "--observations", exists=True, readable=True),
    topology: Path | None = typer.Option(None, "--topology", exists=True, readable=True),
    use_model: bool = typer.Option(
        False, "--use-model", help="Opt in to one paid hypothesis-source call."
    ),
    generation_only: bool = typer.Option(False, "--generation-only"),
    store: Path | None = typer.Option(None, "--store", help="Optional local SQLite audit store."),
) -> None:
    """Emit an investigation; unresolved/abstained is valid output, not a CLI failure."""
    try:
        configured = YamlProject.from_file(project)
        supplied = GraphSnapshot.model_validate_json(read_document(topology)) if topology else None
        event = Incident.model_validate_json(read_document(incident))
        facts = (
            TypeAdapter(tuple[Evidence, ...]).validate_json(read_document(observations))
            if observations
            else None
        )
        result = asyncio.run(
            configured.investigate(
                event,
                observations=facts,
                topology=supplied,
                use_model=use_model,
                generation_only=generation_only,
            )
        )
        if store is not None:
            InvestigationStore(store).save(result)
    except Exception as error:
        raise typer.BadParameter(
            "Investigation failed; check documents, scope, dependencies and provider settings."
        ) from error
    typer.echo(json_document(result.model_dump(mode="json")).rstrip())
