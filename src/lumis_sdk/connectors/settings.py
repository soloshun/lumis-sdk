"""Source and registered-query contracts; importable without HTTP or SQL extras."""

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
    # Comma-separated structured-metadata fields to include in each entry (operator allowlist,
    # e.g. "error,dataset"). OTel-shipped logs keep the details there, not in the line.
    fields: Annotated[str, StringConstraints(max_length=300)] = ""

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(name.strip() for name in self.fields.split(",") if name.strip())

    @model_validator(mode="after")
    def validate_selector(self) -> Self:
        # Not a LogQL parser: the server validates syntax. Refuse unscoped selectors locally.
        if not re.search(r'\{[^}]*[A-Za-z_][A-Za-z0-9_]*\s*=\s*"[^"\n]+"', self.logql):
            raise ValueError("Loki requires an exact, nonempty label matcher")
        names = self.field_names
        if (
            len(names) > 5
            or len(set(names)) != len(names)
            or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name) for name in names)
        ):
            raise ValueError("Loki fields must be at most 5 distinct structured-metadata names")
        if names and self.output != "entries":
            raise ValueError("Loki fields apply to entries output only")
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


class SqlSource(Contract):
    """One PostgreSQL database, read through operator-registered scalar queries only.

    The connection string comes from the environment (`dsn_env`), never from configuration.
    Every query runs in a read-only transaction with a statement timeout; use a read-only role
    as well, because the transaction mode is a guard, not a permission boundary.
    """

    enabled: StrictBool = False
    dsn_env: EnvironmentName | None = None
    statement_timeout_ms: int = Field(default=5000, ge=100, le=60000)
    connect_timeout_seconds: int = Field(default=5, ge=1, le=30)
    max_requests: int = Field(default=32, ge=1, le=100)

    @model_validator(mode="after")
    def validate_dsn(self) -> Self:
        if self.enabled and self.dsn_env is None:
            raise ValueError("enabled SQL source requires dsn_env")
        return self


SQL_WINDOW_PARAMETERS = frozenset({"started_at", "ended_at"})


class SqlQuery(Contract):
    """One SELECT returning one row with one column; `%(started_at)s` and `%(ended_at)s` bind
    the incident window. Not a SQL parser: the read-only transaction is the enforcement."""

    sql: Text

    @model_validator(mode="after")
    def validate_statement(self) -> Self:
        statement = self.sql.strip()
        if not re.match(r"(?is)^(select|with)\b", statement):
            raise ValueError("SQL query must be a single SELECT or WITH statement")
        if ";" in statement.rstrip(";") or statement.count(";") > 1:
            raise ValueError("SQL query must be a single statement")
        named = set(re.findall(r"%\((\w+)\)s", statement))
        if not named <= SQL_WINDOW_PARAMETERS:
            raise ValueError("SQL parameters are limited to %(started_at)s and %(ended_at)s")
        if re.search(r"%(?!\(\w+\)s|%)", statement):
            raise ValueError("use %% for a literal percent sign in SQL")
        return self


def change_path(path: str) -> str:
    """A repository-relative file or directory, passed to Git as a literal pathspec."""
    parts = path.removesuffix("/").split("/")  # a trailing slash marks a directory
    if (
        not path
        or path.startswith(("/", "-", ":"))
        or "\\" in path
        or any(part in {"", ".", "..", ".git"} for part in parts)
    ):
        raise ValueError("change paths must be explicit relative repository paths")
    return path


class GitChangeSource(Contract):
    """One repository whose commits are changes to the entities its paths configure."""

    id: Identifier
    root: Text
    # Repository-relative file or directory -> entity IDs it configures (e.g. a GitOps manifest).
    paths: dict[Identifier, tuple[Identifier, ...]] = Field(min_length=1, max_length=200)
    # Optional conventional-commit scopes -> entities, e.g. "feature-service" for
    # "deploy(feature-service): 1.6.0 -> 1.7.0". A recognised scope narrows a commit to a shared
    # file (one kustomization.yaml or values file for many services) to the entities it names.
    scopes: dict[Identifier, tuple[Identifier, ...]] = Field(default_factory=dict, max_length=200)

    @model_validator(mode="after")
    def validate_paths(self) -> Self:
        for path, entity_ids in self.paths.items():
            change_path(path)
            if not entity_ids:
                raise ValueError("each change path must map to at least one entity")
        if any(not entity_ids for entity_ids in self.scopes.values()):
            raise ValueError("each change scope must map to at least one entity")
        return self


class ChangeSource(Contract):
    """Typed, time-bounded change records: commits to mapped paths and Kubernetes rollouts."""

    enabled: StrictBool = False
    git: tuple[GitChangeSource, ...] = Field(default=(), max_length=10)
    kubernetes_rollouts: StrictBool = False
    lookback_seconds: int = Field(default=3600, ge=60, le=604800)
    max_records: int = Field(default=50, ge=1, le=200)

    @model_validator(mode="after")
    def validate_backends(self) -> Self:
        if self.enabled and not (self.git or self.kubernetes_rollouts):
            raise ValueError(
                "enabled change source requires git repositories or kubernetes_rollouts"
            )
        if len({source.id for source in self.git}) != len(self.git):
            raise ValueError("duplicate change repository IDs")
        return self


class ChangeQuery(Contract):
    """A fact about recent changes to the query's entity, counted back from the incident end.

    Query parameters are strings in YAML/JSON (`lookback_seconds: "1800"`)."""

    output: Literal["count", "seconds_since_latest"] = "count"
    lookback_seconds: int | None = Field(default=None, ge=60, le=604800)
    kind: Literal["any", "commit", "rollout"] = "any"
