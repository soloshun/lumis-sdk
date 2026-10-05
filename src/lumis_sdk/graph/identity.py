"""Explicit identity normalization and physical-to-logical service links."""

from lumis_sdk.connectors import merge_topology
from lumis_sdk.core import Entity, GraphSnapshot, Relationship


def link_kubernetes_services(snapshot: GraphSnapshot) -> GraphSnapshot:
    """Use approved app labels/namespace, not workload env, to add logical service identities."""
    logical: dict[str, Entity] = {}
    edges: list[Relationship] = []
    for entity in snapshot.entities:
        name = entity.attributes.get("service.name")
        namespace = entity.attributes.get("namespace")
        if not entity.kind.startswith("kubernetes.") or not name or not namespace:
            continue
        service_id = f"service:{namespace}:{name}"
        logical[service_id] = Entity(
            id=service_id,
            kind="service",
            name=name,
            attributes={"service.namespace": namespace},
            provenance=("kubernetes.app-label",),
        )
        edges.append(
            Relationship(
                source=entity.id,
                target=service_id,
                kind="hosts",
                provenance=("kubernetes.app-label",),
            )
        )
    merged = merge_topology(snapshot, GraphSnapshot(entities=tuple(logical.values())))
    return merge_topology(
        merged, GraphSnapshot(entities=merged.entities, relationships=tuple(edges))
    )


def normalize_identities(
    snapshot: GraphSnapshot,
    aliases: dict[str, str],
    declared: GraphSnapshot,
) -> GraphSnapshot:
    """Rename only explicit IDs; never guess equivalence by a bare name.

    Many-to-one service aliases require compatible kinds/metadata. A declared target may supply
    its human-readable display name. Resource-to-service collapse is rejected.
    """
    targets = {entity.id: entity for entity in declared.entities}
    parts: list[GraphSnapshot] = []
    for entity in snapshot.entities:
        target_id = aliases.get(entity.id, entity.id)
        target_entity = targets.get(target_id)
        if target_entity and target_entity.kind != entity.kind:
            raise ValueError("identity alias cannot collapse incompatible entity kinds")
        renamed = entity.model_copy(
            update={
                "id": target_id,
                "name": target_entity.name if target_entity else entity.name,
            }
        )
        parts.append(GraphSnapshot(entities=(renamed,)))
    entities = merge_topology(*parts).entities
    edges: dict[tuple[str, str, str], Relationship] = {}
    for edge in snapshot.relationships:
        source, target = (
            aliases.get(edge.source, edge.source),
            aliases.get(edge.target, edge.target),
        )
        # Aliasing two views of one identity removes only the artificial self relationship.
        if source == target and edge.source != edge.target:
            continue
        key = (source, target, edge.kind)
        previous = edges.get(key)
        edges[key] = edge.model_copy(
            update={
                "source": source,
                "target": target,
                "provenance": tuple(
                    sorted(set(edge.provenance) | set(previous.provenance if previous else ()))
                ),
            }
        )
    return GraphSnapshot(
        entities=entities, relationships=tuple(edges[key] for key in sorted(edges))
    )
