"""Public YAML-to-investigation composition, shared by Python, notebooks and the CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import SecretStr, TypeAdapter

from lumis_sdk.connectors import SnapshotConnector
from lumis_sdk.core import Evidence, GraphSnapshot, Incident, Investigation
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.reasoning import HypothesisSource, ModelHypothesisSource, RuleSource
from lumis_sdk.runtime.discovery import (
    DiscoveryReport,
    discover_project,
    http_client,
    relative_path,
)
from lumis_sdk.runtime.documents import read_document
from lumis_sdk.runtime.investigation import EvidenceConnector, InvestigationRuntime
from lumis_sdk.runtime.project import OperationalProject, load_project

if TYPE_CHECKING:
    import httpx

    from lumis_sdk.checks import TriageGuard
    from lumis_sdk.investigation.contracts import IncidentReport
    from lumis_sdk.runtime.incident_handler import Investigator
    from lumis_sdk.sandbox.runner import ProbeRunner


@dataclass(frozen=True)
class PreparedProject:
    """A discovered, reference-bound estate; reuse it explicitly or prepare a fresh snapshot."""

    config: OperationalProject
    base: Path
    graph: OperationalGraph
    discovery: DiscoveryReport

    async def handle_incident(
        self,
        incident: Incident,
        *,
        observations: tuple[Evidence, ...] | None = None,
        use_agent: bool = False,
        investigator: Investigator | None = None,
        guard: TriageGuard | None = None,
        runner: ProbeRunner | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> IncidentReport:
        """Context → evidence-backed triage → optional tool-using agent → human review."""
        from lumis_sdk.runtime.incident_handler import handle_incident

        project = self.config
        if observations is None and project.observations_file is not None:
            observations = TypeAdapter(tuple[Evidence, ...]).validate_json(
                read_document(relative_path(self.base, project.observations_file))
            )
        connectors: dict[str, EvidenceConnector] = {
            "snapshot": SnapshotConnector(observations or ())
        }
        if runner is None and project.investigator.sandbox.enabled:
            from lumis_sdk.sandbox.runner import DockerProbeRunner

            runner = DockerProbeRunner(project.investigator.sandbox)
        async with http_client(
            client,
            required=project.sources.prometheus.enabled,
            timeout=project.budget.query_timeout_seconds,
        ) as connection:
            if project.sources.prometheus.enabled:
                from lumis_sdk.connectors.prometheus import PrometheusConnector

                assert connection is not None and project.sources.prometheus.endpoint is not None
                connectors["prometheus"] = PrometheusConnector(
                    project.sources.prometheus.endpoint, connection
                )
            return await handle_incident(
                project,
                self.graph,
                incident,
                connectors=connectors,
                base=self.base,
                use_agent=use_agent,
                investigator=investigator,
                guard=guard,
                runner=runner,
            )

    async def investigate(
        self,
        incident: Incident,
        *,
        observations: tuple[Evidence, ...] | None = None,
        use_model: bool = False,
        generation_only: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> Investigation:
        """No rediscovery or implicit paid call; missing observations remain unknown."""
        project = self.config
        if observations is None and project.observations_file is not None:
            observations = TypeAdapter(tuple[Evidence, ...]).validate_json(
                read_document(relative_path(self.base, project.observations_file))
            )
        sources: list[HypothesisSource] = [RuleSource(project.rule_hypotheses)]
        connectors: dict[str, EvidenceConnector] = {
            "snapshot": SnapshotConnector(observations or ())
        }
        async with http_client(
            client,
            required=project.sources.prometheus.enabled or use_model,
            timeout=max(
                project.budget.query_timeout_seconds, project.budget.source_timeout_seconds
            ),
        ) as connection:
            if project.sources.prometheus.enabled:
                from lumis_sdk.connectors.prometheus import PrometheusConnector

                assert connection is not None and project.sources.prometheus.endpoint is not None
                connectors["prometheus"] = PrometheusConnector(
                    project.sources.prometheus.endpoint, connection
                )
            if use_model:
                if project.models is None:
                    raise ValueError("explicit model configuration required")
                from lumis_sdk.models.factory import create_hypothesis_model

                assert connection is not None
                sources.append(
                    ModelHypothesisSource(
                        create_hypothesis_model(
                            provider=project.models.provider,
                            model=project.models.model,
                            api_key=SecretStr(os.environ.get(project.models.credential_env, "")),
                            client=connection,
                            max_input_characters=project.budget.max_context_characters,
                            max_output_tokens=project.budget.max_model_output_tokens,
                        )
                    )
                )
            return await InvestigationRuntime(
                graph=self.graph,
                queries=project.queries,
                sources=sources,
                connectors=connectors,
                budget=project.budget,
            ).investigate(
                incident,
                initial_query_ids=project.initial_query_ids,
                generation_only=generation_only,
            )


@dataclass(frozen=True)
class YamlProject:
    config: OperationalProject
    base: Path

    @classmethod
    def from_file(cls, path: str | Path) -> YamlProject:
        """Validate local YAML only; source discovery starts at prepare/investigate."""
        resolved = Path(path).resolve()
        return cls(load_project(resolved), resolved.parent)

    async def prepare(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        at: datetime | None = None,
        topology: GraphSnapshot | None = None,
    ) -> PreparedProject:
        config = self.config.model_copy(deep=True)
        report = await discover_project(config, self.base, client=client, at=at, topology=topology)
        config.validate_references(report.graph)
        return PreparedProject(config, self.base, OperationalGraph(report.graph), report)

    async def investigate(
        self,
        incident: Incident,
        *,
        observations: tuple[Evidence, ...] | None = None,
        use_model: bool = False,
        generation_only: bool = False,
        client: httpx.AsyncClient | None = None,
        topology: GraphSnapshot | None = None,
    ) -> Investigation:
        """Prepare at the incident end time, then run a separately bounded investigation."""
        prepared = await self.prepare(client=client, at=incident.ended_at, topology=topology)
        return await prepared.investigate(
            incident,
            observations=observations,
            use_model=use_model,
            generation_only=generation_only,
            client=client,
        )

    async def handle_incident(
        self,
        incident: Incident,
        *,
        observations: tuple[Evidence, ...] | None = None,
        use_agent: bool = False,
        investigator: Investigator | None = None,
        guard: TriageGuard | None = None,
        runner: ProbeRunner | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> IncidentReport:
        prepared = await self.prepare(client=client, at=incident.ended_at)
        return await prepared.handle_incident(
            incident,
            observations=observations,
            use_agent=use_agent,
            investigator=investigator,
            guard=guard,
            runner=runner,
            client=client,
        )
