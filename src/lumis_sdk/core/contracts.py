"""Validated, serializable facts and falsifiable candidates for a read-only investigation.

Model candidates deliberately cannot carry supporting evidence IDs, execution instructions,
or confirmation state. Those are owned by deterministic evaluation, not generation.
"""

from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    StringConstraints,
    model_validator,
)

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
Scalar = StrictBool | StrictInt | StrictFloat | StrictStr
StopReason = Literal[
    "supported_candidates",
    "budget_exhausted",
    "no_discriminating_query",
    "no_candidates",
    "deadline_exceeded",
    "generation_only",
]


class Contract(BaseModel):
    """Reject unknown fields, NaN, infinity, and attribute reassignment."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, allow_inf_nan=False, revalidate_instances="always"
    )


class Entity(Contract):
    """Operational identity; attributes should contain normalized non-secret metadata only."""

    id: Identifier
    kind: Identifier
    name: Identifier
    attributes: dict[str, str] = Field(default_factory=dict)
    provenance: tuple[Identifier, ...] = ()


class Relationship(Contract):
    """A directed observed or declared relationship, not an inferred causal conclusion."""

    source: Identifier
    target: Identifier
    kind: Identifier
    provenance: tuple[Identifier, ...] = ()


class GraphSnapshot(Contract):
    """An inspectable graph value with unique identities and valid edge endpoints."""

    entities: tuple[Entity, ...] = ()
    relationships: tuple[Relationship, ...] = ()

    @model_validator(mode="after")
    def validate_graph(self) -> "GraphSnapshot":
        ids = {entity.id for entity in self.entities}
        if len(ids) != len(self.entities):
            raise ValueError("graph contains duplicate entity IDs")
        edges = {(edge.source, edge.target, edge.kind) for edge in self.relationships}
        if len(edges) != len(self.relationships):
            raise ValueError("graph contains duplicate relationships")
        if any(edge.source not in ids or edge.target not in ids for edge in self.relationships):
            raise ValueError("relationship endpoint is absent from graph")
        return self


class Incident(Contract):
    """An explicit bounded observation window; synthetic ground truth is never a field."""

    id: Identifier
    affected_entities: tuple[Identifier, ...] = Field(min_length=1, max_length=100)
    symptoms: tuple[Text, ...] = Field(min_length=1, max_length=100)
    started_at: AwareDatetime
    ended_at: AwareDatetime

    @model_validator(mode="after")
    def validate_window(self) -> "Incident":
        if self.ended_at < self.started_at:
            raise ValueError("incident window is reversed")
        return self


class EvidenceQuery(Contract):
    """An operator-registered observation. A model may request its ID, never invent its query."""

    id: Identifier
    provider: Identifier
    entity_id: Identifier
    key: Identifier
    description: Text
    parameters: dict[str, str] = Field(default_factory=dict)


class Evidence(Contract):
    """One normalized tool observation with provenance and observation time."""

    id: Identifier
    query_id: Identifier
    entity_id: Identifier
    key: Identifier
    value: Scalar
    observed_at: AwareDatetime
    source: Identifier
    retrieval_method: Identifier
    quality: Literal["observed", "degraded"] = "observed"


class Check(Contract):
    """A testable prediction or falsifier evaluated only against tool observations."""

    entity_id: Identifier
    key: Identifier
    operator: Literal["eq", "ne", "gt", "ge", "lt", "le"]
    value: Scalar

    @model_validator(mode="after")
    def validate_numeric_comparison(self) -> "Check":
        if self.operator not in {"eq", "ne"} and (
            isinstance(self.value, bool) or not isinstance(self.value, (int, float))
        ):
            raise ValueError("ordered comparison requires a numeric value")
        return self


class Hypothesis(Contract):
    """A candidate explanation, never a confirmed root cause or permission to act."""

    id: Identifier
    statement: Text
    causal_path: tuple[Identifier, ...] = Field(min_length=1, max_length=100)
    predictions: tuple[Check, ...] = Field(min_length=1, max_length=50)
    evidence_needed: tuple[Identifier, ...] = Field(min_length=1, max_length=100)
    falsifiers: tuple[Check, ...] = Field(min_length=1, max_length=50)


class IncidentContext(Contract):
    """The bounded context shared by every hypothesis source."""

    incident: Incident
    graph: GraphSnapshot
    queries: tuple[EvidenceQuery, ...]
    evidence: tuple[Evidence, ...] = ()

    @model_validator(mode="after")
    def validate_references(self) -> "IncidentContext":
        ids = {entity.id for entity in self.graph.entities}
        if not set(self.incident.affected_entities) <= ids:
            raise ValueError("affected entity is absent from incident graph")
        query_ids = {query.id for query in self.queries}
        if len(query_ids) != len(self.queries):
            raise ValueError("duplicate query IDs")
        if any(query.entity_id not in ids for query in self.queries):
            raise ValueError("query target is absent from incident graph")
        if len({item.id for item in self.evidence}) != len(self.evidence):
            raise ValueError("duplicate evidence IDs")
        catalog = {query.id: query for query in self.queries}
        for item in self.evidence:
            query = catalog.get(item.query_id)
            if query is None or (item.entity_id, item.key) != (query.entity_id, query.key):
                raise ValueError("evidence does not match registered query")
            if not self.incident.started_at <= item.observed_at <= self.incident.ended_at:
                raise ValueError("evidence timestamp is outside incident window")
        return self


class InvestigationBudget(Contract):
    """Hard limits for one run, including deterministic and model sources."""

    graph_hops: int = Field(default=3, ge=0, le=20)
    max_entities: int = Field(default=100, ge=1, le=10000)
    max_queries: int = Field(default=8, ge=0, le=1000)
    max_hypotheses: int = Field(default=5, ge=1, le=50)
    max_model_output_tokens: int = Field(default=3000, ge=1, le=32000)
    max_context_characters: int = Field(default=20000, ge=1, le=1000000)
    query_timeout_seconds: float = Field(default=10, gt=0, le=300)
    source_timeout_seconds: float = Field(default=30, gt=0, le=300)
    total_timeout_seconds: float = Field(default=120, gt=0, le=3600)


class HypothesisAssessment(Contract):
    """Mechanical check results; support is not calibrated probability or confirmed truth."""

    hypothesis: Hypothesis
    sources: tuple[Identifier, ...]
    state: Literal["supported", "contradicted", "unresolved"]
    supporting_evidence_ids: tuple[Identifier, ...] = ()
    contradicting_evidence_ids: tuple[Identifier, ...] = ()
    missing_checks: tuple[Check, ...] = ()


class TraceStep(Contract):
    """A reproducible audit event without wall-clock timing or provider exception details."""

    kind: Literal["source", "query", "stop"]
    reference: Identifier
    reason: Text
    hypothesis_ids: tuple[Identifier, ...] = ()
    status: Literal["ok", "error", "timeout", "rejected"] = "ok"


class Investigation(Contract):
    """Versioned terminal result including abstention, with no action or confirmation authority."""

    api_version: Literal["lumis.dev/operational-v1alpha1"] = "lumis.dev/operational-v1alpha1"
    sdk_version: Identifier
    context: IncidentContext
    assessments: tuple[HypothesisAssessment, ...]
    trace: tuple[TraceStep, ...]
    outcome: Literal["supported", "abstained", "hypotheses_ready"]
    stop_reason: StopReason
    truth_state: Literal["unconfirmed_hypothesis"] = "unconfirmed_hypothesis"

    @model_validator(mode="after")
    def validate_assessment_references(self) -> "Investigation":
        ids = {item.id for item in self.context.evidence}
        for assessment in self.assessments:
            validate_hypothesis(assessment.hypothesis, self.context)
            references = (
                *assessment.supporting_evidence_ids,
                *assessment.contradicting_evidence_ids,
            )
            if not set(references) <= ids:
                raise ValueError("assessment references unknown evidence")
        return self


def validate_hypothesis(hypothesis: Hypothesis, context: IncidentContext) -> None:
    """Enforce graph and tool-catalog membership before accepting a candidate."""
    validate_hypothesis_catalog(hypothesis, context.graph, context.queries)


def validate_hypothesis_catalog(
    hypothesis: Hypothesis, graph: GraphSnapshot, catalog: tuple[EvidenceQuery, ...]
) -> None:
    """Validate candidate references without constructing a fictitious incident context."""
    ids = {entity.id for entity in graph.entities}
    targets = {check.entity_id for check in (*hypothesis.predictions, *hypothesis.falsifiers)}
    if not (set(hypothesis.causal_path) | targets) <= ids:
        raise ValueError("hypothesis references entity outside incident graph")
    validate_hypothesis_queries(hypothesis, catalog)


def validate_hypothesis_queries(hypothesis: Hypothesis, catalog: tuple[EvidenceQuery, ...]) -> None:
    """Validate query coverage before topology discovery or source registration."""
    queries = {query.id: query for query in catalog}
    if not set(hypothesis.evidence_needed) <= queries.keys():
        raise ValueError("hypothesis requests unregistered evidence")
    available = {
        (queries[query_id].entity_id, queries[query_id].key)
        for query_id in hypothesis.evidence_needed
    }
    if any(
        (check.entity_id, check.key) not in available
        for check in (*hypothesis.predictions, *hypothesis.falsifiers)
    ):
        raise ValueError("hypothesis check cannot be tested by registered queries")
