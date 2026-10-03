"""HTTP source and registered-query contracts; importable without HTTP extras."""

import re
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import BeforeValidator, Field, StrictBool, StringConstraints, model_validator

from lumis_sdk.core.contracts import Contract, Identifier, Text

EnvironmentName = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]*$")]


def canonical_trace_id(value: object) -> str:
    """Tempo search omits leading zeroes; OTLP uses fixed-width trace identities."""
    if not isinstance(value, str) or not re.fullmatch(r"[a-fA-F0-9]{1,32}", value):
        raise ValueError("invalid hexadecimal trace ID")
    if int(value, 16) == 0:
        raise ValueError("zero trace ID is invalid")
    return value.lower().zfill(32)


TraceID = Annotated[
    str, BeforeValidator(canonical_trace_id), StringConstraints(pattern=r"^[a-f0-9]{32}$")
]


class RemoteSource(Contract):
    enabled: StrictBool = False
    endpoint: Text | None = None
    headers_env: dict[Literal["Authorization", "X-Scope-OrgID"], EnvironmentName] = Field(
        default_factory=dict
    )
    max_response_bytes: int = Field(default=1_000_000, ge=1, le=10_000_000)
    max_results: int = Field(default=50, ge=1, le=100)
    max_requests: int = Field(default=32, ge=1, le=100)

    @model_validator(mode="after")
    def validate_remote(self) -> Self:
        if self.enabled and self.endpoint is None:
            raise ValueError("enabled HTTP source requires endpoint")
        if self.endpoint is not None:
            url = urlsplit(self.endpoint)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
            ):
                raise ValueError("invalid source endpoint")
        return self


class LokiSource(RemoteSource):
    """Read-only log queries; no ingestion, tailing or deletion."""


class TempoSource(RemoteSource):
    discover_trace_ids: tuple[TraceID, ...] = Field(default=(), max_length=10)
    discovery_query: Text | None = None
    lookback_seconds: int = Field(default=3600, ge=1, le=86400)
    service_namespace: Identifier | None = None
    max_spans: int = Field(default=1000, ge=1, le=10000)
    max_trace_reads: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def validate_discovery(self) -> Self:
        if (self.discover_trace_ids or self.discovery_query) and (
            not self.enabled or not self.service_namespace
        ):
            raise ValueError("Tempo discovery requires enabled source and service_namespace")
        if self.discovery_query:
            TempoQuery(traceql=self.discovery_query)
        if len(set(self.discover_trace_ids)) != len(self.discover_trace_ids):
            raise ValueError("duplicate discovery trace IDs")
        return self


class PrefectSource(RemoteSource):
    flow_names: tuple[Identifier, ...] = Field(default=(), max_length=50)
    discover_topology: StrictBool = False
    namespace: Identifier | None = None
    lookback_seconds: int = Field(default=3600, ge=1, le=86400)

    @model_validator(mode="after")
    def validate_scope(self) -> Self:
        if self.enabled and not self.flow_names:
            raise ValueError("Prefect requires an explicit flow_names allowlist")
        if len(set(self.flow_names)) != len(self.flow_names):
            raise ValueError("duplicate Prefect flow names")
        if self.discover_topology and (not self.enabled or not self.namespace):
            raise ValueError("Prefect discovery requires enabled source and namespace")
        return self


class LokiQuery(Contract):
    logql: Text
    output: Literal["entries", "count"] = "entries"

    @model_validator(mode="after")
    def validate_selector(self) -> Self:
        # Not a LogQL parser: the server validates syntax. Refuse unscoped selectors locally.
        if not re.search(r'\{[^}]*[A-Za-z_][A-Za-z0-9_]*\s*=\s*"[^"\n]+"', self.logql):
            raise ValueError("Loki requires an exact, nonempty label matcher")
        return self


class TempoQuery(Contract):
    traceql: Text | None = None
    trace_id: TraceID | None = None
    output: Literal["entries", "duration_ms", "spans"] = "entries"

    @model_validator(mode="after")
    def validate_operation(self) -> Self:
        if bool(self.traceql) == bool(self.trace_id):
            raise ValueError("Tempo requires exactly one of traceql or trace_id")
        if self.traceql and not re.search(r'\bresource\.[\w.]+\s*=\s*"[^"\n]+"', self.traceql):
            raise ValueError("Tempo search requires an exact resource matcher")
        if self.trace_id and self.output != "spans":
            raise ValueError("trace_id queries require output: spans")
        return self


class PrefectQuery(Contract):
    flow_name: Identifier
    operation: Literal["flow_runs", "task_runs"] = "flow_runs"
    flow_run_id: Annotated[str, StringConstraints(pattern=r"^[a-fA-F0-9-]{36}$")] | None = None
    output: Literal["entries", "failed_count", "max_duration_ms"] = "entries"

    @model_validator(mode="after")
    def validate_operation(self) -> Self:
        if self.operation == "task_runs" and not self.flow_run_id:
            raise ValueError("Prefect task queries require flow_run_id")
        if self.operation == "flow_runs" and self.flow_run_id:
            raise ValueError("flow_run_id is only supported for task queries")
        if self.flow_run_id:
            from uuid import UUID

            UUID(self.flow_run_id)
        return self
