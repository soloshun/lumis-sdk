"""Public reference-agent contracts; no hidden reasoning, confirmation or execution authority."""

from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, StrictBool, StringConstraints, model_validator

from lumis_sdk.core import Hypothesis, HypothesisAssessment, IncidentContext
from lumis_sdk.core.contracts import Contract, Identifier, Text, validate_hypothesis


class DiagnosticRule(Contract):
    id: Identifier
    hypothesis: Hypothesis
    terminal: StrictBool = False
    explains_entities: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def require_sufficient_observables(self) -> Self:
        if (
            self.terminal
            and len({(check.entity_id, check.key) for check in self.hypothesis.predictions}) < 2
        ):
            raise ValueError(
                "terminal signature requires at least two distinct predicted observables"
            )
        return self


class Finding(Contract):
    rule_id: Identifier
    status: Literal["match", "no_match", "unknown"]
    terminal: StrictBool
    assessment: HypothesisAssessment

    @property
    def display_status(self) -> str:
        return {
            "match": "matched",
            "no_match": "did not match (ruled out)",
            "unknown": "can't tell",
        }[self.status]


class AgentBudget(Contract):
    request_limit: int = Field(default=8, ge=1, le=30)
    tool_calls_limit: int = Field(default=10, ge=1, le=100)
    max_probes: int = Field(default=2, ge=0, le=10)
    output_tokens_limit: int = Field(default=12000, ge=100, le=100000)
    max_tool_characters: int = Field(default=8000, ge=100, le=64000)
    max_total_tool_characters: int = Field(default=32000, ge=100, le=256000)
    # Malformed tool arguments or a rejected final answer are returned to the model this many
    # times (the validation error is the retry message); attempts still count toward the budgets.
    validation_retries: int = Field(default=2, ge=0, le=5)
    initial_candidates: int = Field(default=5, ge=1, le=5)
    followup_candidates: int = Field(default=3, ge=0, le=3)


class InspectRequest(Contract):
    operation: Literal[
        "catalog",
        "graph",
        "evidence",
        "code.read",
        "code.search",
        "git.log",
        "git.diff",
        "changes",
        "hypothesis.register",
    ]
    target: Identifier | None = None
    query_id: Identifier | None = None
    path: Identifier | None = None
    text: Text | None = None
    base_commit: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{40}$")] | None = None
    head_commit: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{40}$")] | None = None
    hypothesis: Hypothesis | None = None


class ProbeSpec(Contract):
    hypothesis_id: Identifier
    query_id: Identifier
    purpose: Text
    code: Annotated[str, StringConstraints(min_length=1, max_length=16000)]
    repository: Identifier | None = None


class CandidateState(Contract):
    """A bounded mechanical state update, never model reasoning or a probability."""

    hypothesis_id: Identifier
    state: Literal["supported", "contradicted", "unresolved"]
    supporting_evidence_ids: tuple[Identifier, ...] = ()
    contradicting_evidence_ids: tuple[Identifier, ...] = ()
    missing_check_count: int = Field(ge=0)


class ToolReceipt(Contract):
    """Digest identifies full safe UTF-8 output before truncation, not model visibility."""

    id: Identifier
    operation: Identifier
    status: Literal["ok", "error", "denied", "timeout"]
    purpose: Text
    output: str = Field(max_length=64000)
    digest: Identifier
    hypothesis_id: Identifier | None = None
    code_digest: Identifier | None = None
    snapshot_digest: Identifier | None = None
    reason_code: Identifier | None = None
    truncated: StrictBool = False
    output_digest: Identifier | None = None
    original_characters: int | None = Field(default=None, ge=0)
    cached_from: Identifier | None = None
    warnings: tuple[Text, ...] = ()
    assessments: tuple[CandidateState, ...] = ()
    assessments_truncated: StrictBool = False


class Suggestion(Contract):
    hypothesis_id: Identifier
    description: Text
    evidence_ids: tuple[Identifier, ...] = ()
    receipt_ids: tuple[Identifier, ...] = ()
    patch: str | None = Field(default=None, max_length=16000)
    requires_human_review: Literal[True] = True


class AgentOutput(Contract):
    """Untrusted candidate material: the model cannot author assessments or evidence."""

    hypotheses: tuple[Hypothesis, ...] = Field(default=(), max_length=5)
    suggestions: tuple[Suggestion, ...] = Field(default=(), max_length=5)
    unresolved_questions: tuple[Text, ...] = Field(default=(), max_length=10)


class RunMetrics(Contract):
    model_requests: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)

    @property
    def cache_read_share(self) -> float:
        return self.cache_read_tokens / self.input_tokens if self.input_tokens else 0.0

    tool_attempts: int = Field(default=0, ge=0)
    evidence_queries: int = Field(default=0, ge=0)
    probes: int = Field(default=0, ge=0)


class IncidentReport(Contract):
    api_version: Literal["lumis.dev/incident-report-v1alpha1"] = (
        "lumis.dev/incident-report-v1alpha1"
    )
    sdk_version: Identifier
    context: IncidentContext
    findings: tuple[Finding, ...]
    assessments: tuple[HypothesisAssessment, ...]
    receipts: tuple[ToolReceipt, ...] = ()
    suggestions: tuple[Suggestion, ...] = ()
    unresolved_questions: tuple[Text, ...] = ()
    route: Literal["deterministic", "agent", "human"]
    conclusion: Literal["supported_diagnosis", "insufficient_evidence", "requires_human_expert"]
    stop_reason: Identifier
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    truth_state: Literal["unconfirmed_hypothesis"] = "unconfirmed_hypothesis"
    requires_human_review: Literal[True] = True
    warnings: tuple[Text, ...] = ()

    def markdown(self) -> str:
        """Render a cited, unconfirmed human-review account; never a second model call."""
        from lumis_sdk.investigation.render import report_markdown

        return report_markdown(self)

    @model_validator(mode="after")
    def validate_links(self) -> Self:
        evidence_ids = {item.id for item in self.context.evidence}
        hypotheses = {item.hypothesis.id for item in self.assessments}
        receipt_ids = {item.id for item in self.receipts}
        if len(hypotheses) != len(self.assessments) or len(receipt_ids) != len(self.receipts):
            raise ValueError("duplicate report identities")
        for assessment in (*self.assessments, *(finding.assessment for finding in self.findings)):
            validate_hypothesis(assessment.hypothesis, self.context)
            if (
                not set(
                    (*assessment.supporting_evidence_ids, *assessment.contradicting_evidence_ids)
                )
                <= evidence_ids
            ):
                raise ValueError("unknown assessment evidence")
        prior_receipts: set[str] = set()
        for receipt in self.receipts:
            if receipt.cached_from is not None and receipt.cached_from not in prior_receipts:
                raise ValueError("cached receipt must reference an earlier receipt")
            for state in receipt.assessments:
                if state.hypothesis_id not in hypotheses:
                    raise ValueError("unknown provisional hypothesis")
                if (
                    not set((*state.supporting_evidence_ids, *state.contradicting_evidence_ids))
                    <= evidence_ids
                ):
                    raise ValueError("unknown provisional evidence")
            prior_receipts.add(receipt.id)
        for suggestion in self.suggestions:
            if suggestion.hypothesis_id not in hypotheses:
                raise ValueError("unknown suggestion hypothesis")
            if (
                not set(suggestion.evidence_ids) <= evidence_ids
                or not set(suggestion.receipt_ids) <= receipt_ids
            ):
                raise ValueError("unknown suggestion evidence/receipt")
        if self.conclusion == "supported_diagnosis" and not any(
            item.state == "supported" for item in self.assessments
        ):
            raise ValueError("supported diagnosis requires mechanical support")
        return self


class HumanResolution(Contract):
    """Separate append-only human attestation, not an agent's confirmed-cause claim."""

    id: Identifier
    incident_id: Identifier
    reviewer: Identifier
    recorded_at: AwareDatetime
    summary: Text
    applied_change: Text
    outcome: Literal["resolved", "not_resolved", "inconclusive"]
    evidence_references: tuple[Text, ...] = Field(default=(), max_length=20)
    source: Literal["human"] = "human"
