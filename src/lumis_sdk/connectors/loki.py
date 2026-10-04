"""Bounded LogQL log observations, never ingestion or remediation."""

from lumis_sdk.connectors.remote import RemoteConnector, nanoseconds
from lumis_sdk.connectors.settings import LokiQuery
from lumis_sdk.core import Evidence, EvidenceQuery, Incident


def _field(metadata: dict, name: str, label: object) -> object:  # type: ignore[type-arg]
    """A structured-metadata value from a categorized response, else the stream label."""
    for group in ("structuredMetadata", "parsed"):
        values = metadata.get(group)
        if isinstance(values, dict) and name in values:
            return values[name]
    return label


class LokiConnector(RemoteConnector):
    async def collect(self, query: EvidenceQuery, incident: Incident) -> tuple[Evidence, ...]:
        parameters = LokiQuery.model_validate(query.parameters)
        path = "/loki/api/v1/query_range"
        payload = await self.request(
            "GET",
            path,
            params={
                "query": parameters.logql,
                "start": incident.started_at.isoformat(),
                "end": incident.ended_at.isoformat(),
                "limit": self.source.max_results,
                "direction": "forward",
            },
        )
        if not isinstance(payload, dict):
            raise ValueError("invalid Loki response")
        if payload.get("status") != "success" or payload.get("warnings"):
            raise ValueError("Loki query unsuccessful or partial")
        data = payload["data"]
        if data["resultType"] != "streams":
            raise ValueError("registered Loki query must return log streams")
        rows: list[tuple[str, str, dict[str, str]]] = []
        for stream in data["result"]:
            labels = stream.get("stream") or {}
            for row in stream["values"]:
                # Loki may append structured metadata; only operator-allowlisted fields are
                # exported (from the row's metadata or the stream's labels), bounded and redacted.
                if len(row) not in {2, 3} or not isinstance(row[1], str):
                    raise ValueError("invalid log row")
                metadata = row[2] if len(row) == 3 and isinstance(row[2], dict) else {}
                extra = {
                    name: str(value)[:600]
                    for name in parameters.field_names
                    if (value := _field(metadata, name, labels.get(name))) is not None
                }
                rows.append((row[0], row[1], extra))
                if len(rows) > self.source.max_results:
                    raise ValueError("Loki result limit exceeded")
        if not rows:
            return ()  # No records is not proof of absence or complete telemetry coverage.
        times = [nanoseconds(row[0]) for row in rows]
        if any(not incident.started_at <= at <= incident.ended_at for at in times):
            raise ValueError("Loki returned out-of-window records")
        capped = len(rows) == self.source.max_results
        if parameters.output == "count":
            return (
                self.fact(
                    query, incident, len(rows), max(times), 0, "GET " + path, degraded=capped
                ),
            )
        return tuple(
            self.fact(
                query,
                incident,
                self.text({"timestamp": at.isoformat(), "message": row[1], **row[2]}),
                at,
                index,
                "GET " + path,
                degraded=capped,
            )
            for index, (row, at) in enumerate(zip(rows, times, strict=True))
        )
