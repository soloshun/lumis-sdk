"""Deterministic indexed traversal over a validated snapshot.

Edges point from producer/dependency to consumer/dependent. Incident neighborhoods use both
directions; upstream and downstream traversals preserve direction. Cycles are supported.
"""

from collections import defaultdict, deque
from collections.abc import Iterable

from lumis_sdk.core import GraphSnapshot


class OperationalGraph:
    """Immutable snapshot plus O(V+E) adjacency indexes, built once per estate."""

    def __init__(self, snapshot: GraphSnapshot) -> None:
        self._snapshot = snapshot.model_copy(deep=True)
        self._entities = {entity.id: entity for entity in self._snapshot.entities}
        self._upstream: dict[str, set[str]] = defaultdict(set)
        self._downstream: dict[str, set[str]] = defaultdict(set)
        for edge in snapshot.relationships:
            self._downstream[edge.source].add(edge.target)
            self._upstream[edge.target].add(edge.source)
        self._adjacent = {
            node: self._upstream[node] | self._downstream[node] for node in self._entities
        }

    def snapshot(self) -> GraphSnapshot:
        """Return an independent serializable value."""
        return self._snapshot.model_copy(deep=True)

    def upstream_of(self, node: str, *, hops: int = 3, max_entities: int = 100) -> tuple[str, ...]:
        """Return transitive dependency IDs, excluding the seed."""
        return tuple(sorted(self._walk((node,), self._upstream, hops, max_entities) - {node}))

    def downstream_of(
        self, node: str, *, hops: int = 3, max_entities: int = 100
    ) -> tuple[str, ...]:
        """Return transitive dependent IDs, excluding the seed."""
        return tuple(sorted(self._walk((node,), self._downstream, hops, max_entities) - {node}))

    def scope(
        self, nodes: Iterable[str], *, hops: int = 3, max_entities: int = 100
    ) -> GraphSnapshot:
        """Extract a bounded neighborhood; refuse overflow rather than silently drop entities."""
        ids = self._walk(nodes, self._adjacent, hops, max_entities)
        return GraphSnapshot(
            entities=tuple(self._entities[node] for node in sorted(ids)),
            relationships=tuple(
                sorted(
                    (
                        edge
                        for edge in self._snapshot.relationships
                        if edge.source in ids and edge.target in ids
                    ),
                    key=lambda edge: (edge.source, edge.target, edge.kind),
                )
            ),
        )

    def _walk(
        self, seeds: Iterable[str], adjacency: dict[str, set[str]], hops: int, limit: int
    ) -> set[str]:
        if hops < 0 or limit < 1:
            raise ValueError("hops must be nonnegative and max_entities must be positive")
        visited = set(seeds)
        if not visited <= self._entities.keys():
            raise ValueError("unknown graph seed")
        if len(visited) > limit:
            raise ValueError("incident graph exceeds entity budget")
        queue = deque((seed, 0) for seed in sorted(visited))
        while queue:
            node, depth = queue.popleft()
            if depth == hops:
                continue
            for neighbor in sorted(adjacency.get(node, set())):
                if neighbor not in visited:
                    if len(visited) >= limit:
                        raise ValueError("incident graph exceeds entity budget")
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        return visited
