"""Scoped Prefect 3 read-only filter APIs, run evidence and observed task relationships."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from lumis_sdk.connectors.remote import RemoteConnector, numeric, timestamp
from lumis_sdk.connectors.settings import PrefectQuery, PrefectSource
from lumis_sdk.core import Entity, Evidence, EvidenceQuery, GraphSnapshot, Incident, Relationship


def run_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid Prefect run ID")
    return str(UUID(value))


class PrefectConnector(RemoteConnector):
    source: PrefectSource

    async def runs(
        self,
        flow_name: str,
        operation: str,
        start: datetime,
        end: datetime,
        *,
        flow_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if flow_name not in self.source.flow_names:
            raise ValueError("Prefect flow outside source allowlist")
        if operation not in {"flow_runs", "task_runs"}:
            raise ValueError("unsupported Prefect read operation")
        filters: dict[str, Any] = {
            "flows": {"name": {"any_": [flow_name]}},
            "limit": self.source.max_results,
            "offset": 0,
            "sort": "START_TIME_ASC" if operation == "flow_runs" else "EXPECTED_START_TIME_ASC",
            operation: {"start_time": {"after_": start.isoformat(), "before_": end.isoformat()}},
        }
        if operation == "task_runs":
            if not flow_run_id:
                raise ValueError("task read requires explicit flow run")
            filters["flow_runs"] = {"id": {"any_": [run_id(flow_run_id)]}}
        rows = await self.request("POST", f"/{operation}/filter", json=filters)
        if not isinstance(rows, list) or len(rows) > self.source.max_results:
            raise ValueError("invalid or oversized Prefect filter response")
        seen: set[str] = set()
        for row in rows:
            identity = run_id(row["id"])
            if identity in seen:
                raise ValueError("duplicate Prefect run identity")
            seen.add(identity)
            if not start <= timestamp(row["start_time"]) <= end:
                raise ValueError("Prefect returned out-of-window run")
            if operation == "task_runs" and run_id(row["flow_run_id"]) != flow_run_id:
                raise ValueError("Prefect task belongs to another flow run")
        return rows

    async def collect(self, query: EvidenceQuery, incident: Incident) -> tuple[Evidence, ...]:
        parameters = PrefectQuery.model_validate(query.parameters)
        rows = await self.runs(
            parameters.flow_name,
            parameters.operation,
            incident.started_at,
            incident.ended_at,
            flow_run_id=parameters.flow_run_id,
        )
        if not rows:
            return ()
        observations: list[tuple[dict[str, Any], datetime]] = []
        for row in rows:
            # Current-state APIs cannot reconstruct a historical state. Refuse a state that
            # transitioned outside the incident; do not relabel it as an incident-time fact.
            state = row["state"]
            if state["type"] not in {
                "SCHEDULED",
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                "CRASHED",
                "PAUSED",
                "CANCELLING",
            }:
                raise ValueError("unknown Prefect state type")
            at = timestamp(state["timestamp"])
            if not timestamp(row["start_time"]) <= at <= incident.ended_at:
                raise ValueError("Prefect state transition is outside incident window")
            if row.get("end_time") is not None:
                end = timestamp(row["end_time"])
                if not timestamp(row["start_time"]) <= end <= incident.ended_at:
                    raise ValueError("Prefect run end is outside incident window")
            duration_ms = numeric(row["total_run_time"]) * 1000
            observations.append(
                (
                    {
                        "run_id": run_id(row["id"]),
                        "name": row["name"],
                        "flow_name": parameters.flow_name,
                        "state": state["type"],
                        "state_timestamp": at.isoformat(),
                        "duration_ms": duration_ms,
                        "start": row["start_time"],
                        "end": row.get("end_time"),
                    },
                    at,
                )
            )
        capped = len(rows) == self.source.max_results
        path = f"POST /{parameters.operation}/filter (read-only)"
        if parameters.output != "entries":
            value = (
                sum(row["state"] in {"FAILED", "CRASHED"} for row, _ in observations)
                if parameters.output == "failed_count"
                else max(row["duration_ms"] for row, _ in observations)
            )
            return (
                self.fact(
                    query,
                    incident,
                    value,
                    max(at for _, at in observations),
                    0,
                    path,
                    degraded=capped,
                ),
            )
        return tuple(
            self.fact(query, incident, self.text(row), at, index, path, degraded=capped)
            for index, (row, at) in enumerate(observations)
        )

    async def discover(
        self,
        *,
        at: datetime | None = None,
        max_entities: int = 5000,
        max_relationships: int = 10000,
    ) -> GraphSnapshot:
        at = at or datetime.now(UTC)
        start = at - timedelta(seconds=self.source.lookback_seconds)
        entities: dict[str, Entity] = {}
        edges: dict[tuple[str, str, str], Relationship] = {}

        def entity(item: Entity) -> None:
            if item.id not in entities and len(entities) >= max_entities:
                raise ValueError("Prefect entity budget exceeded")
            entities[item.id] = item

        def edge(source: str, target: str, kind: str) -> None:
            if (source, target, kind) not in edges and len(edges) >= max_relationships:
                raise ValueError("Prefect relationship budget exceeded")
            edges[source, target, kind] = Relationship(
                source=source, target=target, kind=kind, provenance=("prefect.task_runs",)
            )

        for name in self.source.flow_names:
            rows = await self.runs(name, "flow_runs", start, at)
            if len(rows) == self.source.max_results:
                raise ValueError("Prefect topology may be truncated; narrow discovery window")
            if not rows:
                continue  # Never fabricate an observed flow from config alone.
            flow = f"workflow:{self.source.namespace}:{name}"
            entity(Entity(id=flow, kind="workflow", name=name, provenance=("prefect.flow_runs",)))
            for row in rows:
                identity = run_id(row["id"])
                parent = "prefect:flow-run:" + identity
                entity(
                    Entity(
                        id=parent,
                        kind="flow_run",
                        name=row["name"],
                        provenance=("prefect.flow_runs",),
                    )
                )
                edge(parent, flow, "instance_of")
                tasks = await self.runs(name, "task_runs", start, at, flow_run_id=identity)
                if len(tasks) == self.source.max_results:
                    raise ValueError("Prefect task topology may be truncated")
                task_ids = {run_id(task["id"]) for task in tasks}
                for task in tasks:
                    child = "prefect:task-run:" + run_id(task["id"])
                    entity(
                        Entity(
                            id=child,
                            kind="task_run",
                            name=task["name"],
                            provenance=("prefect.task_runs",),
                        )
                    )
                    edge(child, parent, "part_of")
                    for dependencies in task.get("task_inputs", {}).values():
                        for dependency in dependencies:
                            if dependency.get("input_type") == "task_run":
                                upstream = run_id(dependency["id"])
                                if upstream in task_ids:
                                    edge("prefect:task-run:" + upstream, child, "feeds")
        return GraphSnapshot(entities=tuple(entities.values()), relationships=tuple(edges.values()))
