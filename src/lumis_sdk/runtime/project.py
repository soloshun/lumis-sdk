"""Standalone operational project configuration; no consuming application imports."""

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, StrictBool, StringConstraints, model_validator

from lumis_sdk.connectors.settings import (
    LokiQuery,
    LokiSource,
    PrefectQuery,
    PrefectSource,
    SqlQuery,
    SqlSource,
    TempoQuery,
    TempoSource,
)
from lumis_sdk.core import EvidenceQuery, GraphSnapshot, Hypothesis, InvestigationBudget
from lumis_sdk.core.contracts import (
    Contract,
    Identifier,
    Text,
    validate_hypothesis_catalog,
    validate_hypothesis_queries,
)
from lumis_sdk.investigation.config import InvestigatorSettings
from lumis_sdk.investigation.contracts import DiagnosticRule
from lumis_sdk.runtime.documents import load_mapping, read_document

__all__ = ["OperationalProject", "load_project", "read_document"]


class ProjectIdentity(Contract):
    name: Identifier
    environment: Identifier = "local"


class KubernetesSource(Contract):
    enabled: StrictBool = False
    context: Identifier | None = None
    namespace: Identifier | None = None

    @model_validator(mode="after")
    def require_scope(self) -> Self:
        if self.enabled and (not self.context or not self.namespace):
            raise ValueError("enabled Kubernetes source requires context and namespace")
        return self


class PrometheusSource(Contract):
    enabled: StrictBool = False
    endpoint: str | None = None
    discover_service_graph: StrictBool = False
    service_namespace: Identifier | None = None
    service_graph_query: Text = (
        "sum by (client, server) (rate(traces_service_graph_request_total[5m]))"
    )

    @model_validator(mode="after")
    def require_endpoint(self) -> Self:
        if self.enabled and not self.endpoint:
            raise ValueError("enabled Prometheus source requires endpoint")
        if self.discover_service_graph and (not self.enabled or not self.service_namespace):
            raise ValueError(
                "service graph requires enabled Prometheus and explicit service namespace"
            )
        if self.endpoint:
            # Endpoint validation has no dependency on the optional HTTP implementation.
            from urllib.parse import urlsplit

            parsed = urlsplit(self.endpoint)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("invalid Prometheus endpoint")
        return self


class OpenTelemetrySource(Contract):
    """Normalize an OTLP JSON export; this is not a live OTLP receiver."""

    enabled: StrictBool = False
    export_file: str | None = None

    @model_validator(mode="after")
    def require_export(self) -> Self:
        if self.enabled and not self.export_file:
            raise ValueError("enabled OpenTelemetry source requires export_file")
        return self


class TopologySource(Contract):
    """An external normalized graph snapshot, never executable adapter code."""

    enabled: StrictBool = False
    file_path: Text | None = None

    @model_validator(mode="after")
    def require_file(self) -> Self:
        if self.enabled and not self.file_path:
            raise ValueError("enabled topology source requires file_path")
        return self


class IdentitySettings(Contract):
    aliases: dict[Identifier, Identifier] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_chains(self) -> Self:
        if set(self.aliases.values()) & self.aliases.keys():
            raise ValueError("identity alias chains, self aliases and cycles are not supported")
        return self


class DiscoveryBudget(Contract):
    timeout_seconds: float = Field(default=30, gt=0, le=120)
    max_entities: int = Field(default=5000, ge=1, le=50000)
    max_relationships: int = Field(default=10000, ge=1, le=100000)
    max_service_graph_series: int = Field(default=1000, ge=1, le=10000)
    max_response_bytes: int = Field(default=2000000, ge=1, le=10000000)


class Sources(Contract):
    kubernetes: KubernetesSource = Field(default_factory=KubernetesSource)
    prometheus: PrometheusSource = Field(default_factory=PrometheusSource)
    opentelemetry: OpenTelemetrySource = Field(default_factory=OpenTelemetrySource)
    topology: TopologySource = Field(default_factory=TopologySource)
    loki: LokiSource = Field(default_factory=LokiSource)
    tempo: TempoSource = Field(default_factory=TempoSource)
    prefect: PrefectSource = Field(default_factory=PrefectSource)
    sql: SqlSource = Field(default_factory=SqlSource)

    @property
    def requires_http(self) -> bool:
        return any(
            source.enabled for source in (self.prometheus, self.loki, self.tempo, self.prefect)
        )


class ModelSettings(Contract):
    provider: Literal["openrouter", "openai", "anthropic", "gemini"] = "openrouter"
    model: Identifier
    api_key_env: Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]*$")] | None = None
    # Provider reasoning effort for the reference agent; None leaves the provider default.
    reasoning: Literal["minimal", "low", "medium", "high"] | None = None

    @property
    def credential_env(self) -> str:
        """Provider-specific default, never silently use another provider's key."""
        return (
            self.api_key_env
            or {
                "openrouter": "OPENROUTER_API_KEY",
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "gemini": "GEMINI_API_KEY",
            }[self.provider]
        )


class Policies(Contract):
    """The current kernel cannot execute actions, regardless of model confidence."""

    default_action_mode: Literal["read_only"] = "read_only"


class OperationalProject(Contract):
    api_version: Literal["lumis.dev/operational-v1alpha1"] = "lumis.dev/operational-v1alpha1"
    project: ProjectIdentity
    sources: Sources = Field(default_factory=Sources)
    identity: IdentitySettings = Field(default_factory=IdentitySettings)
    discovery: DiscoveryBudget = Field(default_factory=DiscoveryBudget)
    observations_file: Text | None = None
    models: ModelSettings | None = None
    checks: tuple[DiagnosticRule, ...] = ()
    investigator: InvestigatorSettings = Field(default_factory=InvestigatorSettings)
    policies: Policies = Field(default_factory=Policies)
    graph: GraphSnapshot = Field(default_factory=GraphSnapshot)
    queries: tuple[EvidenceQuery, ...] = ()
    initial_query_ids: tuple[Identifier, ...] = ()
    rule_hypotheses: tuple[Hypothesis, ...] = ()
    budget: InvestigationBudget = Field(default_factory=InvestigationBudget)

    @model_validator(mode="after")
    def validate_catalog(self) -> Self:
        query_ids = {query.id for query in self.queries}
        if len(query_ids) != len(self.queries):
            raise ValueError("duplicate query IDs")
        if len(set(self.initial_query_ids)) != len(self.initial_query_ids):
            raise ValueError("duplicate initial query IDs")
        if not set(self.initial_query_ids) <= query_ids:
            raise ValueError("initial query is not registered")
        for query in self.queries:
            if query.provider not in {
                "snapshot",
                "prometheus",
                "probe",
                "loki",
                "tempo",
                "prefect",
                "sql",
            }:
                raise ValueError("unsupported CLI evidence provider")
            remote: dict[str, type[Contract]] = {
                "loki": LokiQuery,
                "tempo": TempoQuery,
                "prefect": PrefectQuery,
                "sql": SqlQuery,
            }
            if query.provider in remote:
                if not getattr(self.sources, query.provider).enabled:
                    raise ValueError("query requires enabled source")
                parameters = remote[query.provider].model_validate(query.parameters)
                if isinstance(parameters, PrefectQuery):
                    if parameters.flow_name not in self.sources.prefect.flow_names:
                        raise ValueError("Prefect query flow is outside configured allowlist")
            if query.provider == "prometheus":
                if not self.sources.prometheus.enabled or not query.parameters.get("promql"):
                    raise ValueError("Prometheus query requires enabled source and promql")
            if query.provider == "probe" and not self.investigator.sandbox.enabled:
                raise ValueError("probe query requires explicitly enabled sandbox")
        if len({rule.id for rule in self.checks}) != len(self.checks):
            raise ValueError("duplicate diagnostic rule IDs")
        if len(self.checks) > 50:
            raise ValueError("diagnostic check count exceeds bound")
        for rule in self.checks:
            validate_hypothesis_queries(rule.hypothesis, self.queries)
            if rule.terminal and not rule.explains_entities:
                raise ValueError("terminal check requires explicit explanation scope")
            if not set(rule.explains_entities) <= set(rule.hypothesis.causal_path):
                raise ValueError("explanation scope must belong to candidate path")
            if any(
                query.provider == "probe" and query.id in rule.hypothesis.evidence_needed
                for query in self.queries
            ):
                raise ValueError("deterministic checks cannot use agent-authored probes")
        if len({item.id for item in self.rule_hypotheses}) != len(self.rule_hypotheses):
            raise ValueError("duplicate hypothesis IDs")
        for hypothesis in self.rule_hypotheses:
            validate_hypothesis_queries(hypothesis, self.queries)
        if not self.requires_discovery:
            self.validate_references(self.graph)
        return self

    @property
    def requires_discovery(self) -> bool:
        return bool(
            self.sources.kubernetes.enabled
            or self.sources.opentelemetry.enabled
            or self.sources.topology.enabled
            or self.sources.prometheus.discover_service_graph
            or self.sources.prefect.discover_topology
            or self.sources.tempo.discover_trace_ids
            or self.sources.tempo.discovery_query
        )

    def validate_references(self, graph: GraphSnapshot) -> None:
        """Bind IDs only after enabled discovery; unresolved references fail closed."""
        ids = {entity.id for entity in graph.entities}
        if any(query.entity_id not in ids for query in self.queries):
            raise ValueError("query entity absent from prepared graph")
        for hypothesis in self.rule_hypotheses:
            validate_hypothesis_catalog(hypothesis, graph, self.queries)
        for rule in self.checks:
            validate_hypothesis_catalog(rule.hypothesis, graph, self.queries)
        if any(not set(repo.entity_ids) <= ids for repo in self.investigator.repositories):
            raise ValueError("repository mapping references absent entity")


def load_project(path: Path) -> OperationalProject:
    """Parse and validate local configuration only; never discover or invoke a model."""
    return OperationalProject.model_validate(load_mapping(path))
