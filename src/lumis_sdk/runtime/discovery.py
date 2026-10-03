"""Bounded topology discovery with explicit per-source results and fail-closed preparation."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Self

from pydantic import Field, StrictBool, model_validator

from lumis_sdk.connectors import merge_topology
from lumis_sdk.connectors.kubernetes import KubernetesDiscovery
from lumis_sdk.connectors.otel import topology_from_otlp
from lumis_sdk.core import GraphSnapshot
from lumis_sdk.core.contracts import Contract
from lumis_sdk.graph.identity import link_kubernetes_services, normalize_identities
from lumis_sdk.runtime.documents import read_document
from lumis_sdk.runtime.project import OperationalProject

if TYPE_CHECKING:
    import httpx


class SourceDiscovery(Contract):
    name: str
    status: Literal["ok", "error", "disabled", "not_checked"]
    entities: int = Field(default=0, ge=0)
    relationships: int = Field(default=0, ge=0)
    reason: str | None = None


class DiscoveryReport(Contract):
    graph: GraphSnapshot
    sources: tuple[SourceDiscovery, ...]
    complete: StrictBool = True

    @model_validator(mode="after")
    def validate_completion(self) -> Self:
        ready = all(source.status in {"ok", "disabled"} for source in self.sources)
        if self.complete != ready:
            raise ValueError("discovery completion must agree with source statuses")
        return self


class DiscoveryError(ValueError):
    """A partial graph is diagnostic only, never an investigation-ready estate."""

    def __init__(self, report: DiscoveryReport) -> None:
        super().__init__("Topology discovery incomplete; inspect source statuses and bounds")
        self.report = report


@asynccontextmanager
async def http_client(
    client: httpx.AsyncClient | None, *, required: bool, timeout: float
) -> AsyncIterator[httpx.AsyncClient | None]:
    """Caller owns an injected client; core-only/offline paths do not import HTTP extras."""
    if client is not None or not required:
        yield client
        return
    import httpx

    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as owned:
        yield owned


def relative_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


async def discover_project(
    config: OperationalProject,
    base: Path,
    *,
    client: httpx.AsyncClient | None = None,
    at: datetime | None = None,
    topology: GraphSnapshot | None = None,
) -> DiscoveryReport:
    """Merge enabled sources, refusing incomplete discovery, collisions and aggregate overflow.

    Sources are acquired serially under one discovery deadline. No query/entity placeholders,
    namespace guesses or consumer imports are used. Cancellation propagates to the caller.
    """
    if at is not None and (at.tzinfo is None or at.utcoffset() is None):
        raise ValueError("discovery time must be timezone aware")
    enabled = {
        "declared": True,
        "supplied": topology is not None,
        "topology": config.sources.topology.enabled,
        "kubernetes": config.sources.kubernetes.enabled,
        "opentelemetry": config.sources.opentelemetry.enabled,
        "prometheus.service_graph": config.sources.prometheus.discover_service_graph,
    }
    statuses = {
        name: SourceDiscovery(name=name, status="not_checked" if active else "disabled")
        for name, active in enabled.items()
    }
    merged = GraphSnapshot()
    current = "declared"

    def accept(name: str, snapshot: GraphSnapshot) -> None:
        nonlocal merged
        normalized = normalize_identities(snapshot, config.identity.aliases, config.graph)
        candidate = merge_topology(merged, normalized)
        if (
            len(candidate.entities) > config.discovery.max_entities
            or len(candidate.relationships) > config.discovery.max_relationships
        ):
            raise ValueError("aggregate topology exceeds discovery budget")
        merged = candidate
        statuses[name] = SourceDiscovery(
            name=name,
            status="ok",
            entities=len(normalized.entities),
            relationships=len(normalized.relationships),
        )

    try:
        async with asyncio.timeout(config.discovery.timeout_seconds):
            accept("declared", config.graph)
            if topology is not None:
                current = "supplied"
                accept(current, topology)
            if enabled["topology"]:
                current = "topology"
                assert config.sources.topology.file_path is not None
                accept(
                    current,
                    GraphSnapshot.model_validate_json(
                        read_document(relative_path(base, config.sources.topology.file_path))
                    ),
                )
            if enabled["kubernetes"]:
                current = "kubernetes"
                kube = config.sources.kubernetes
                assert kube.context is not None and kube.namespace is not None
                snapshot = await KubernetesDiscovery(
                    context=kube.context,
                    namespace=kube.namespace,
                    timeout_seconds=config.discovery.timeout_seconds,
                    max_response_bytes=config.discovery.max_response_bytes,
                ).discover()
                accept(current, link_kubernetes_services(snapshot))
            if enabled["opentelemetry"]:
                current = "opentelemetry"
                assert config.sources.opentelemetry.export_file is not None
                payload = json.loads(
                    read_document(relative_path(base, config.sources.opentelemetry.export_file))
                )
                accept(current, topology_from_otlp(payload))
            if enabled["prometheus.service_graph"]:
                current = "prometheus.service_graph"
                from lumis_sdk.connectors.service_graph import PrometheusServiceGraph

                prometheus = config.sources.prometheus
                assert prometheus.endpoint is not None and prometheus.service_namespace is not None
                async with http_client(
                    client, required=True, timeout=config.discovery.timeout_seconds
                ) as connection:
                    assert connection is not None
                    accept(
                        current,
                        await PrometheusServiceGraph(prometheus.endpoint, connection).discover(
                            query=prometheus.service_graph_query,
                            namespace=prometheus.service_namespace,
                            at=at,
                            max_series=config.discovery.max_service_graph_series,
                            max_bytes=config.discovery.max_response_bytes,
                        ),
                    )
    except Exception as error:
        # Do not export provider errors/URLs/bodies/credentials in readiness output.
        statuses[current] = SourceDiscovery(
            name=current,
            status="error",
            reason="Source unavailable, invalid, conflicting or over discovery bounds",
        )
        raise DiscoveryError(
            DiscoveryReport(graph=merged, sources=tuple(statuses.values()), complete=False)
        ) from error
    return DiscoveryReport(graph=merged, sources=tuple(statuses.values()))
