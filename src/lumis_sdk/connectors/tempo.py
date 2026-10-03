"""TraceQL summaries and OTLP spans from the Tempo query frontend."""

import base64
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import TypeAdapter

from lumis_sdk.connectors.otel import topology_from_otlp
from lumis_sdk.connectors.remote import RemoteConnector, nanoseconds, numeric
from lumis_sdk.connectors.settings import TempoQuery, TempoSource, TraceID
from lumis_sdk.core import Evidence, EvidenceQuery, GraphSnapshot, Incident


class TempoConnector(RemoteConnector):
    source: TempoSource

    async def trace(self, trace_id: str) -> dict[str, Any]:
        trace_id = TypeAdapter(TraceID).validate_python(trace_id)
        payload = await self.request("GET", "/api/traces/" + trace_id)
        if not isinstance(payload, dict):
            raise ValueError("invalid Tempo trace")
        # Tempo's OTLP JSON uses batches; standard OTLP exports use resourceSpans.
        resources = payload.get("batches", payload.get("resourceSpans"))
        if not isinstance(resources, list):
            raise ValueError("Tempo trace missing OTLP resources")
        count = 0
        for resource in resources:
            scopes = resource.get("scopeSpans", resource.get("instrumentationLibrarySpans", []))
            resource["scopeSpans"] = scopes
            for scope in scopes:
                for span in scope.get("spans", []):
                    count += 1
                    if count > self.source.max_spans:
                        raise ValueError("Tempo span budget exceeded")
                    for key, widths in (
                        ("traceId", (8, 16)),
                        ("spanId", (8,)),
                        ("parentSpanId", (8,)),
                    ):
                        value = span.get(key, "")
                        if not value and key == "parentSpanId":
                            continue
                        if not isinstance(value, str):
                            raise ValueError("invalid OTLP identifier")
                        if re.fullmatch(r"[a-fA-F0-9]+", value) and len(value) in (
                            width * 2 for width in widths
                        ):
                            span[key] = value.lower()
                        else:
                            decoded = base64.b64decode(value, validate=True)
                            if len(decoded) not in widths:
                                raise ValueError("invalid OTLP identifier length")
                            span[key] = decoded.hex()
                        if key == "traceId":
                            span[key] = span[key].zfill(32)
                    if span["traceId"] != trace_id.lower():
                        raise ValueError("Tempo trace identity mismatch")
        return {"resourceSpans": resources}

    async def discover(
        self,
        *,
        at: datetime | None = None,
        max_entities: int = 5000,
        max_relationships: int = 10000,
    ) -> GraphSnapshot:
        from lumis_sdk.connectors import merge_topology

        graph = GraphSnapshot()
        trace_ids = list(self.source.discover_trace_ids)
        if self.source.discovery_query:
            end = at or datetime.now(UTC)
            start = end - timedelta(seconds=self.source.lookback_seconds)
            payload = await self.request(
                "GET",
                "/api/search",
                params={
                    "q": self.source.discovery_query,
                    "start": int(start.timestamp()),
                    "end": int(end.timestamp()) + 1,
                    "limit": 11,
                },
            )
            if not isinstance(payload, dict):
                raise ValueError("invalid Tempo discovery response")
            rows = payload.get("traces", [])
            if not isinstance(rows, list) or len(rows) > 10 or payload.get("warnings"):
                raise ValueError("Tempo discovery search incomplete or exceeds trace budget")
            for row in rows:
                if not start <= nanoseconds(row["startTimeUnixNano"]) <= end:
                    raise ValueError("Tempo discovery trace outside window")
                trace_ids.append(TypeAdapter(TraceID).validate_python(row["traceID"]))
        if len(set(trace_ids)) > 10:
            raise ValueError("Tempo discovery trace budget exceeded")
        for trace_id in dict.fromkeys(trace_ids):
            payload = await self.trace(trace_id)
            snapshot = topology_from_otlp(payload, max_spans=self.source.max_spans)
            entities = tuple(
                entity
                for entity in snapshot.entities
                if entity.attributes.get("service.namespace") == self.source.service_namespace
            )
            ids = {entity.id for entity in entities}
            graph = merge_topology(
                graph,
                GraphSnapshot(
                    entities=entities,
                    relationships=tuple(
                        edge
                        for edge in snapshot.relationships
                        if edge.source in ids and edge.target in ids
                    ),
                ),
            )
            if len(graph.entities) > max_entities or len(graph.relationships) > max_relationships:
                raise ValueError("Tempo topology budget exceeded")
        return graph

    async def collect(self, query: EvidenceQuery, incident: Incident) -> tuple[Evidence, ...]:
        parameters = TempoQuery.model_validate(query.parameters)
        if parameters.trace_id:
            payload = await self.trace(parameters.trace_id)
            facts: list[Evidence] = []
            for resource in payload["resourceSpans"]:
                identity = {
                    attribute["key"]: attribute.get("value", {}).get("stringValue")
                    for attribute in resource.get("resource", {}).get("attributes", [])
                    if attribute["key"] in {"service.name", "service.namespace"}
                }
                for scope in resource.get("scopeSpans", []):
                    for span in scope.get("spans", []):
                        start, end = (
                            nanoseconds(span["startTimeUnixNano"]),
                            nanoseconds(span["endTimeUnixNano"]),
                        )
                        if end < start:
                            raise ValueError("reversed span window")
                        if not incident.started_at <= start <= end <= incident.ended_at:
                            continue
                        if len(facts) >= self.source.max_results:
                            raise ValueError("Tempo observation budget exceeded")
                        facts.append(
                            self.fact(
                                query,
                                incident,
                                self.text(
                                    {
                                        "trace_id": parameters.trace_id,
                                        "span_id": span["spanId"],
                                        "parent_span_id": span.get("parentSpanId"),
                                        "service": identity,
                                        "name": span.get("name"),
                                        "duration_ms": (end - start).total_seconds() * 1000,
                                        "status_code": span.get("status", {}).get("code"),
                                    }
                                ),
                                end,
                                len(facts),
                                "GET /api/traces/{traceID}",
                            )
                        )
            return tuple(facts)
        payload = await self.request(
            "GET",
            "/api/search",
            params={
                "q": parameters.traceql,
                "start": int(incident.started_at.timestamp()),
                "end": int(incident.ended_at.timestamp()) + 1,
                "limit": self.source.max_results,
            },
        )
        if not isinstance(payload, dict):
            raise ValueError("invalid Tempo search response")
        rows = payload.get("traces", [])
        if not isinstance(rows, list) or len(rows) > self.source.max_results:
            raise ValueError("Tempo result bound exceeded")
        if payload.get("warnings"):
            raise ValueError("partial Tempo search")
        result: list[Evidence] = []
        seen: set[str] = set()
        for row in rows:
            trace_id = TypeAdapter(TraceID).validate_python(row["traceID"])
            if trace_id in seen:
                raise ValueError("duplicate trace search record")
            seen.add(trace_id)
            at = nanoseconds(row["startTimeUnixNano"])
            duration = numeric(row["durationMs"])
            if at + timedelta(milliseconds=duration) > incident.ended_at:
                raise ValueError("trace duration extends outside incident window")
            value = (
                duration
                if parameters.output == "duration_ms"
                else self.text(
                    {
                        "trace_id": trace_id,
                        "start": at.isoformat(),
                        "duration_ms": duration,
                        "root_service": row.get("rootServiceName"),
                        "root_span": row.get("rootTraceName"),
                    }
                )
            )
            result.append(
                self.fact(
                    query,
                    incident,
                    value,
                    at,
                    len(result),
                    "GET /api/search",
                    degraded=len(rows) == self.source.max_results,
                )
            )
        return tuple(result)
