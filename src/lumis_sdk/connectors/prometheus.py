"""Read-only instant PromQL observations using caller-registered queries."""

from datetime import UTC, datetime

import httpx

from lumis_sdk.connectors.http import read_json, validate_endpoint
from lumis_sdk.core import Evidence, EvidenceQuery, Incident


class PrometheusConnector:
    """Query a configured endpoint. Own and close the injected HTTP client's lifetime."""

    def __init__(self, endpoint: str, client: httpx.AsyncClient) -> None:
        self.endpoint = validate_endpoint(endpoint)
        self.client = client

    async def collect(self, query: EvidenceQuery, incident: Incident) -> tuple[Evidence, ...]:
        """Require one scalar or one vector sample; multi-series aggregation is caller-owned."""
        expression = query.parameters.get("promql")
        if not expression:
            raise ValueError("registered query requires promql")
        payload = await read_json(
            self.client,
            "GET",
            self.endpoint + "/api/v1/query",
            params={
                "query": expression,
                "time": incident.ended_at.timestamp(),
            },
        )
        if payload.get("status") != "success":
            raise ValueError("Prometheus query unsuccessful")
        data = payload["data"]
        if data["resultType"] == "scalar":
            timestamp, value = data["result"]
        elif data["resultType"] == "vector" and len(data["result"]) == 1:
            timestamp, value = data["result"][0]["value"]
        else:
            raise ValueError("Prometheus query must produce exactly one numeric sample")
        return (
            Evidence(
                id=f"prometheus:{query.id}",
                query_id=query.id,
                entity_id=query.entity_id,
                key=query.key,
                value=float(value),
                observed_at=datetime.fromtimestamp(float(timestamp), UTC),
                source="prometheus",
                retrieval_method="GET /api/v1/query",
            ),
        )
