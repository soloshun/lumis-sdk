"""NetworkX-backed operational graph with deterministic, bounded traversal."""

from __future__ import annotations

import copy
import json
from collections import deque
from collections.abc import Callable, Iterable
from typing import Any

import networkx as nx

from lumis_sdk.core import GraphSnapshot


class OperationalGraph:
    """A validated snapshot backed by a directed multigraph.

    Multiple relationship kinds between the same entities are preserved. Edges represent
    observed/declared relationships, not proven causality. Public exports are independent copies.
    """

    def __init__(self, snapshot: GraphSnapshot) -> None:
        self._snapshot = GraphSnapshot.model_validate(snapshot.model_dump())
        self._entities = {entity.id: entity for entity in self._snapshot.entities}
        self._graph: nx.MultiDiGraph[str, dict[str, Any], dict[str, Any]] = nx.MultiDiGraph()
        for entity in self._snapshot.entities:
            self._graph.add_node(entity.id, **entity.model_dump(exclude={"id"}))
        for edge in self._snapshot.relationships:
            self._graph.add_edge(
                edge.source,
                edge.target,
                key=edge.kind,
                **edge.model_dump(exclude={"source", "target"}),
            )
        self._edges = {
            (edge.source, edge.target, edge.kind): edge for edge in self._snapshot.relationships
        }

    def snapshot(self) -> GraphSnapshot:
        return self._snapshot.model_copy(deep=True)

    def to_networkx(self) -> nx.MultiDiGraph[str, dict[str, Any], dict[str, Any]]:
        """Return a deep copy for inspection/algorithms/drawing, never a live kernel view."""
        return copy.deepcopy(self._graph)

    def to_dot(self) -> str:
        """Export inspectable DOT without Graphviz or plotting dependencies; quote all text."""
        lines = ["digraph lumis {"]
        for entity in sorted(self._snapshot.entities, key=lambda item: item.id):
            lines.append(f"  {json.dumps(entity.id)} [label={json.dumps(entity.name)}];")
        for edge in sorted(
            self._snapshot.relationships, key=lambda item: (item.source, item.target, item.kind)
        ):
            lines.append(
                f"  {json.dumps(edge.source)} -> {json.dumps(edge.target)} "
                f"[label={json.dumps(edge.kind)}];"
            )
        return "\n".join([*lines, "}"])

    def upstream_of(self, node: str, *, hops: int = 3, max_entities: int = 100) -> tuple[str, ...]:
        """Dependency IDs excluding the seed, with a hard entity limit."""
        return tuple(
            sorted(self._walk((node,), self._graph.predecessors, hops, max_entities) - {node})
        )

    def downstream_of(
        self, node: str, *, hops: int = 3, max_entities: int = 100
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._walk((node,), self._graph.successors, hops, max_entities) - {node})
        )

    def dependencies_within(
        self, node: str, *, hops: int = 3, max_entities: int = 100
    ) -> GraphSnapshot:
        """Incident-relevant neighborhood in both directions, including the seed."""
        return self.scope((node,), hops=hops, max_entities=max_entities)

    def scope(
        self, nodes: Iterable[str], *, hops: int = 3, max_entities: int = 100
    ) -> GraphSnapshot:
        """Refuse overflow rather than silently dropping topology."""

        def neighbors(node: str) -> Iterable[str]:
            return set(self._graph.predecessors(node)) | set(self._graph.successors(node))

        ids = self._walk(nodes, neighbors, hops, max_entities)
        subgraph = self._graph.subgraph(ids)
        edge_keys = sorted(subgraph.edges(keys=True))
        return GraphSnapshot(
            entities=tuple(self._entities[node].model_copy(deep=True) for node in sorted(ids)),
            relationships=tuple(self._edges[key].model_copy(deep=True) for key in edge_keys),
        )

    def _walk(
        self, seeds: Iterable[str], neighbors: Callable[[str], Iterable[str]], hops: int, limit: int
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
            for neighbor in sorted(neighbors(node)):
                if neighbor not in visited:
                    if len(visited) >= limit:
                        raise ValueError("incident graph exceeds entity budget")
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        return visited
