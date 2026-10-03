"""Standalone operational project configuration; no consuming application imports."""

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from lumis_sdk.core import EvidenceQuery, GraphSnapshot, Hypothesis, InvestigationBudget
from lumis_sdk.core.contracts import Contract, Identifier, validate_hypothesis_catalog
from lumis_sdk.runtime.documents import load_mapping, read_document

__all__ = ["OperationalProject", "load_project", "read_document"]


class ProjectIdentity(Contract):
    name: Identifier
    environment: Identifier = "local"


class KubernetesSource(Contract):
    enabled: bool = False
    context: Identifier | None = None
    namespace: Identifier | None = None

    @model_validator(mode="after")
    def require_scope(self) -> Self:
        if self.enabled and (not self.context or not self.namespace):
            raise ValueError("enabled Kubernetes source requires context and namespace")
        return self


class PrometheusSource(Contract):
    enabled: bool = False
    endpoint: str | None = None

    @model_validator(mode="after")
    def require_endpoint(self) -> Self:
        if self.enabled and not self.endpoint:
            raise ValueError("enabled Prometheus source requires endpoint")
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

    enabled: bool = False
    export_file: str | None = None

    @model_validator(mode="after")
    def require_export(self) -> Self:
        if self.enabled and not self.export_file:
            raise ValueError("enabled OpenTelemetry source requires export_file")
        return self


class Sources(Contract):
    kubernetes: KubernetesSource = Field(default_factory=KubernetesSource)
    prometheus: PrometheusSource = Field(default_factory=PrometheusSource)
    opentelemetry: OpenTelemetrySource = Field(default_factory=OpenTelemetrySource)


class ModelSettings(Contract):
    provider: Literal["openrouter", "openai", "anthropic", "gemini"] = "openrouter"
    model: Identifier
    api_key_env: Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]*$")] | None = None

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
    models: ModelSettings | None = None
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
        ids = {entity.id for entity in self.graph.entities}
        for query in self.queries:
            if query.entity_id not in ids:
                raise ValueError("query entity absent from declared graph")
            if query.provider not in {"snapshot", "prometheus"}:
                raise ValueError("unsupported CLI evidence provider")
            if query.provider == "prometheus":
                if not self.sources.prometheus.enabled or not query.parameters.get("promql"):
                    raise ValueError("Prometheus query requires enabled source and promql")
        if len({item.id for item in self.rule_hypotheses}) != len(self.rule_hypotheses):
            raise ValueError("duplicate hypothesis IDs")
        for hypothesis in self.rule_hypotheses:
            validate_hypothesis_catalog(hypothesis, self.graph, self.queries)
        return self


def load_project(path: Path) -> OperationalProject:
    """Parse and validate local configuration only; never discover or invoke a model."""
    return OperationalProject.model_validate(load_mapping(path))
