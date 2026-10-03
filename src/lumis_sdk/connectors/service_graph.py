"""Read-only topology from a Prometheus service-graph vector (e.g. Tempo metrics-generator)."""

import math
from datetime import datetime
from typing import Any

import httpx

from lumis_sdk.connectors.http import read_json, validate_endpoint
from lumis_sdk.core import Entity, GraphSnapshot, Relationship


def topology_from_service_graph(
    payload: dict[str, Any],
    *,
    namespace: str,
    max_series: int = 1000,
) -> GraphSnapshot:
    """Server supplies client: dependency-flow orientation, not HTTP request direction."""
    if not namespace or not namespace.strip():
        raise ValueError("service graph requires explicit namespace")
    if payload.get("status") != "success" or payload.get("warnings"):
        raise ValueError("service graph query failed or returned incomplete data warnings")
    data = payload.get("data", {})
    result = data.get("result")
    if data.get("resultType") != "vector" or not isinstance(result, list):
        raise ValueError("service graph requires a vector")
    if max_series < 1 or len(result) > max_series:
        raise ValueError("service graph exceeds series budget")
    entities: dict[str, Entity] = {}
    edges: dict[tuple[str, str, str], Relationship] = {}
    for item in result:
        labels = item.get("metric", {})
        client, server = labels.get("client"), labels.get("server")
        sample = item.get("value", [])
        if (
            not isinstance(client, str)
            or not client.strip()
            or not isinstance(server, str)
            or not server.strip()
        ):
            raise ValueError("service graph requires nonempty client/server labels")
        if (
            len(sample) != 2
            or any(isinstance(value, bool) for value in sample)
            or not all(math.isfinite(float(value)) for value in sample)
        ):
            raise ValueError("service graph sample must be finite")
        if float(sample[1]) < 0:
            raise ValueError("service graph rate cannot be negative")
        if float(sample[1]) == 0:
            continue  # no observed traffic, not evidence of no dependency
        for name in (client, server):
            entity_id = f"service:{namespace}:{name}"
            entities[entity_id] = Entity(
                id=entity_id,
                kind="service",
                name=name,
                attributes={"service.namespace": namespace},
                provenance=("prometheus.service_graph",),
            )
        if client != server:
            edge = Relationship(
                source=f"service:{namespace}:{server}",
                target=f"service:{namespace}:{client}",
                kind="serves",
                provenance=("prometheus.service_graph",),
            )
            edges[(edge.source, edge.target, edge.kind)] = edge
    return GraphSnapshot(
        entities=tuple(entities[key] for key in sorted(entities)),
        relationships=tuple(edges[key] for key in sorted(edges)),
    )


class PrometheusServiceGraph:
    def __init__(self, endpoint: str, client: httpx.AsyncClient) -> None:
        self.endpoint = validate_endpoint(endpoint)
        self.client = client

    async def discover(
        self,
        *,
        query: str,
        namespace: str,
        at: datetime | None = None,
        max_series: int = 1000,
        max_bytes: int = 2_000_000,
    ) -> GraphSnapshot:
        params: dict[str, str | float] = {"query": query}
        if at is not None:
            if at.tzinfo is None or at.utcoffset() is None:
                raise ValueError("discovery time must be timezone aware")
            params["time"] = at.timestamp()
        payload = await read_json(
            self.client, "GET", self.endpoint + "/api/v1/query", params=params, max_bytes=max_bytes
        )
        return topology_from_service_graph(payload, namespace=namespace, max_series=max_series)
