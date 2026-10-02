"""Composition for new read-only commands; legacy commands retain their contracts."""

import asyncio
import json
import os
from pathlib import Path

import typer
from pydantic import SecretStr, TypeAdapter

from lumis_sdk.connectors import SnapshotConnector
from lumis_sdk.connectors.kubernetes import KubernetesDiscovery
from lumis_sdk.core import Evidence, Incident, Investigation
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.reasoning import HypothesisSource, ModelHypothesisSource, RuleSource
from lumis_sdk.runtime import EvidenceConnector, InvestigationRuntime, InvestigationStore
from lumis_sdk.runtime.project import OperationalProject, load_project, read_document


def discover(
    context: str = typer.Option(..., "--context", help="Explicit kubeconfig context."),
    namespace: str = typer.Option(..., "--namespace", help="One namespace, never all namespaces."),
) -> None:
    """Print discovered Kubernetes resources and relationships as JSON; read-only."""
    try:
        graph = asyncio.run(KubernetesDiscovery(context=context, namespace=namespace).discover())
    except Exception as error:
        raise typer.BadParameter(
            "Discovery failed; check context, namespace, RBAC and bounds."
        ) from error
    typer.echo(graph.model_dump_json(indent=2))


def investigate(
    project: Path = typer.Option(..., "--project", exists=True, readable=True),
    incident: Path = typer.Option(..., "--incident", exists=True, readable=True),
    observations: Path | None = typer.Option(None, "--observations", exists=True, readable=True),
    use_model: bool = typer.Option(False, "--use-model", help="Opt in to a paid OpenRouter call."),
    generation_only: bool = typer.Option(False, "--generation-only"),
    store: Path | None = typer.Option(None, "--store", help="Optional local SQLite audit store."),
) -> None:
    """Print a structured investigation. Without a configured live provider, replay local facts."""
    try:
        config = load_project(project)
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
            "Investigation failed; validate documents, scope, optional dependencies "
            "and provider settings."
        ) from error
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))


async def _run(
    project: OperationalProject,
    incident: Incident,
    facts: tuple[Evidence, ...],
    use_model: bool,
    generation_only: bool,
) -> Investigation:
    sources: list[HypothesisSource] = [RuleSource(project.rule_hypotheses)]
    connectors: dict[str, EvidenceConnector] = {"snapshot": SnapshotConnector(facts)}
    if project.prometheus_endpoint or use_model:
        # Lazy imports keep the core offline installation free of HTTP dependencies.
        import httpx

        from lumis_sdk.connectors.prometheus import PrometheusConnector
        from lumis_sdk.models.openrouter import OpenRouterHypothesisModel

        async with httpx.AsyncClient(
            timeout=max(
                project.budget.query_timeout_seconds, project.budget.source_timeout_seconds
            ),
            trust_env=False,
        ) as client:
            if project.prometheus_endpoint:
                connectors["prometheus"] = PrometheusConnector(project.prometheus_endpoint, client)
            if use_model:
                if not project.openrouter_model:
                    raise ValueError("explicit OpenRouter model required")
                sources.append(
                    ModelHypothesisSource(
                        OpenRouterHypothesisModel(
                            model=project.openrouter_model,
                            api_key=SecretStr(os.environ.get("OPENROUTER_API_KEY", "")),
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
