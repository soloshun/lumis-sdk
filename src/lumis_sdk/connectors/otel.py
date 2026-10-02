"""Topology from exported OTLP/JSON traces, without an OTLP receiver or backend dependency."""

from typing import Any

from lumis_sdk.core import Entity, GraphSnapshot, Relationship


def topology_from_otlp(payload: dict[str, Any], *, max_spans: int = 10000) -> GraphSnapshot:
    """Join cross-service parent spans within the same trace.

    A downstream service feeds its caller in dependency-flow orientation. Missing parent spans
    and same-service spans produce no inferred edge. Resource identity uses service.namespace
    and service.name. Span bodies, attributes, baggage, and credentials are never exported.
    """
    if max_spans < 1:
        raise ValueError("positive span budget required")
    entities: dict[str, Entity] = {}
    spans: dict[tuple[str, str], tuple[str, str | None]] = {}
    count = 0
    for resource in payload.get("resourceSpans", []):
        attributes = {
            item["key"]: item.get("value", {}).get("stringValue")
            for item in resource.get("resource", {}).get("attributes", [])
        }
        name = attributes.get("service.name")
        if not name:
            continue
        namespace = attributes.get("service.namespace") or "default"
        entity_id = f"service:{namespace}:{name}"
        entities[entity_id] = Entity(
            id=entity_id,
            kind="service",
            name=name,
            attributes={"service.namespace": namespace},
            provenance=("opentelemetry.resource",),
        )
        for scope in resource.get("scopeSpans", []):
            for span in scope.get("spans", []):
                count += 1
                if count > max_spans:
                    raise ValueError("OTLP span budget exceeded")
                trace_id, span_id = span.get("traceId"), span.get("spanId")
                if not trace_id or not span_id:
                    continue
                key = (trace_id, span_id)
                value = (entity_id, span.get("parentSpanId"))
                if key in spans and spans[key] != value:
                    raise ValueError("conflicting OTLP span identities")
                spans[key] = value
    edges: dict[tuple[str, str], Relationship] = {}
    for (trace_id, _), (child_service, parent_id) in spans.items():
        parent = spans.get((trace_id, parent_id)) if parent_id else None
        if parent and parent[0] != child_service:
            edges[(child_service, parent[0])] = Relationship(
                source=child_service,
                target=parent[0],
                kind="serves",
                provenance=("opentelemetry.parent_span",),
            )
    return GraphSnapshot(
        entities=tuple(entities[key] for key in sorted(entities)),
        relationships=tuple(edges[key] for key in sorted(edges)),
    )
