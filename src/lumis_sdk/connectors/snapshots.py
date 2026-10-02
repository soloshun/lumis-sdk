"""Portable normalized snapshots for offline replay and external estate integration."""

from dataclasses import dataclass

from lumis_sdk.core import Entity, Evidence, EvidenceQuery, GraphSnapshot, Incident, Relationship


@dataclass(frozen=True)
class SnapshotConnector:
    """Replay observations collected outside the application; never import estate modules."""

    evidence: tuple[Evidence, ...]

    async def collect(self, query: EvidenceQuery, incident: Incident) -> tuple[Evidence, ...]:
        return tuple(item for item in self.evidence if item.query_id == query.id)


def merge_topology(*snapshots: GraphSnapshot) -> GraphSnapshot:
    """Combine declared and discovered topology with explicit conflict handling.

    Sources may add attributes/provenance, but conflicting identities or attribute values are
    rejected. Discovery must never silently overwrite declared ownership or business policy.
    """
    entities: dict[str, Entity] = {}
    edges: dict[tuple[str, str, str], Relationship] = {}
    for snapshot in snapshots:
        for entity in snapshot.entities:
            previous = entities.get(entity.id)
            if previous is not None:
                if (previous.kind, previous.name) != (entity.kind, entity.name):
                    raise ValueError("conflicting discovered/declared entity identity")
                if any(
                    previous.attributes[key] != value
                    for key, value in entity.attributes.items()
                    if key in previous.attributes
                ):
                    raise ValueError("conflicting discovered/declared attributes")
                entity = Entity(
                    id=entity.id,
                    kind=entity.kind,
                    name=entity.name,
                    attributes=previous.attributes | entity.attributes,
                    provenance=tuple(sorted(set(previous.provenance) | set(entity.provenance))),
                )
            entities[entity.id] = entity
        for edge in snapshot.relationships:
            key = (edge.source, edge.target, edge.kind)
            previous_edge = edges.get(key)
            edges[key] = edge.model_copy(
                update={
                    "provenance": tuple(
                        sorted(
                            set(edge.provenance)
                            | set(previous_edge.provenance if previous_edge else ())
                        )
                    )
                }
            )
    return GraphSnapshot(
        entities=tuple(entities[key] for key in sorted(entities)),
        relationships=tuple(edges[key] for key in sorted(edges)),
    )
