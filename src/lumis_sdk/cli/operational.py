"""CLI adapters: explicit local reads, opt-in discovery, opt-in paid model calls."""

import asyncio
import importlib.util
import json
import os
import shutil
from pathlib import Path

import typer
from pydantic import SecretStr, TypeAdapter

from lumis_sdk.connectors import SnapshotConnector, merge_topology
from lumis_sdk.connectors.kubernetes import KubernetesDiscovery
from lumis_sdk.connectors.otel import topology_from_otlp
from lumis_sdk.core import Evidence, GraphSnapshot, Incident, Investigation
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.reasoning import HypothesisSource, ModelHypothesisSource, RuleSource
from lumis_sdk.runtime import EvidenceConnector, InvestigationRuntime, InvestigationStore
from lumis_sdk.runtime.documents import json_document
from lumis_sdk.runtime.project import OperationalProject, load_project, read_document


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
) -> None:
    """Merge declared topology with enabled read-only Kubernetes and local OTLP sources."""
    try:
        config = load_project(project)
        graph = asyncio.run(_discover(config, project.parent))
    except Exception as error:
        raise typer.BadParameter(
            "Discovery failed; check configuration, scope, RBAC and bounds."
        ) from error
    typer.echo(graph.model_dump_json(indent=2))


async def _discover(config: OperationalProject, base: Path) -> GraphSnapshot:
    snapshots = [config.graph]
    kube = config.sources.kubernetes
    if kube.enabled:
        assert kube.context is not None and kube.namespace is not None
        snapshots.append(
            await KubernetesDiscovery(context=kube.context, namespace=kube.namespace).discover()
        )
    otel = config.sources.opentelemetry
    if otel.enabled:
        assert otel.export_file is not None
        path = Path(otel.export_file)
        payload = json.loads(read_document(path if path.is_absolute() else base / path))
        snapshots.append(topology_from_otlp(payload))
    return merge_topology(*snapshots)


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
        config = load_project(project)
        if topology:
            graph = GraphSnapshot.model_validate_json(read_document(topology))
            config = OperationalProject.model_validate(
                config.model_dump() | {"graph": merge_topology(config.graph, graph).model_dump()}
            )
        event = Incident.model_validate_json(read_document(incident))
        facts = (
            TypeAdapter(tuple[Evidence, ...]).validate_json(read_document(observations))
            if observations
            else ()
        )
        result = asyncio.run(_run(config, event, facts, use_model, generation_only))
        if store is not None:
            InvestigationStore(store).save(result)
    except Exception as error:
        raise typer.BadParameter(
            "Investigation failed; check documents, scope, dependencies and provider settings."
        ) from error
    typer.echo(json_document(result.model_dump(mode="json")).rstrip())


async def _run(
    project: OperationalProject,
    incident: Incident,
    facts: tuple[Evidence, ...],
    use_model: bool,
    generation_only: bool,
) -> Investigation:
    sources: list[HypothesisSource] = [RuleSource(project.rule_hypotheses)]
    connectors: dict[str, EvidenceConnector] = {"snapshot": SnapshotConnector(facts)}
    if project.sources.prometheus.enabled or use_model:
        import httpx

        from lumis_sdk.connectors.prometheus import PrometheusConnector
        from lumis_sdk.models.factory import create_hypothesis_model

        async with httpx.AsyncClient(
            timeout=max(
                project.budget.query_timeout_seconds, project.budget.source_timeout_seconds
            ),
            trust_env=False,
        ) as client:
            if project.sources.prometheus.enabled:
                assert project.sources.prometheus.endpoint is not None
                connectors["prometheus"] = PrometheusConnector(
                    project.sources.prometheus.endpoint, client
                )
            if use_model:
                if project.models is None:
                    raise ValueError("explicit model configuration required")
                sources.append(
                    ModelHypothesisSource(
                        create_hypothesis_model(
                            provider=project.models.provider,
                            model=project.models.model,
                            api_key=SecretStr(os.environ.get(project.models.credential_env, "")),
                            client=client,
                            max_input_characters=project.budget.max_context_characters,
                            max_output_tokens=project.budget.max_model_output_tokens,
                        )
                    )
                )
            return await _investigate(project, incident, sources, connectors, generation_only)
    return await _investigate(project, incident, sources, connectors, generation_only)


async def _investigate(
    project: OperationalProject,
    incident: Incident,
    sources: list[HypothesisSource],
    connectors: dict[str, EvidenceConnector],
    generation_only: bool,
) -> Investigation:
    return await InvestigationRuntime(
        graph=OperationalGraph(project.graph),
        queries=project.queries,
        sources=sources,
        connectors=connectors,
        budget=project.budget,
    ).investigate(
        incident, initial_query_ids=project.initial_query_ids, generation_only=generation_only
    )
