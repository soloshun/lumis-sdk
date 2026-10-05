"""Scope, propose, seek, evaluate, and retain a terminal result without remediation."""

import asyncio
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Literal, Protocol

from lumis_sdk import __version__
from lumis_sdk.core import (
    Evidence,
    EvidenceQuery,
    Hypothesis,
    HypothesisAssessment,
    Incident,
    IncidentContext,
    Investigation,
    InvestigationBudget,
    TraceStep,
)
from lumis_sdk.core.contracts import StopReason, rejection_reason, validate_hypothesis
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.reasoning import HypothesisSource, assess
from lumis_sdk.security.operational import redact_context


class EvidenceConnector(Protocol):
    """Read-only port for one operator-registered observation."""

    async def collect(self, query: EvidenceQuery, incident: Incident) -> tuple[Evidence, ...]:
        """Return facts matching the registered query and incident window."""
        ...


class InvestigationRuntime:
    """Deterministic orchestration around optional untrusted candidate generators.

    Query selection maximizes coverage of unresolved checks across competing candidates.
    It is an explainable baseline heuristic, not an information-gain/causal algorithm.
    """

    def __init__(
        self,
        *,
        graph: OperationalGraph,
        sources: Sequence[HypothesisSource],
        queries: Sequence[EvidenceQuery],
        connectors: Mapping[str, EvidenceConnector],
        budget: InvestigationBudget | None = None,
    ) -> None:
        self.graph = graph
        self.sources = tuple(sources)
        self.queries = tuple(queries)
        self.connectors = dict(connectors)
        self.budget = budget or InvestigationBudget()
        if len({query.id for query in self.queries}) != len(self.queries):
            raise ValueError("duplicate registered query IDs")
        if len({source.name for source in self.sources}) != len(self.sources):
            raise ValueError("duplicate hypothesis source names")

    async def investigate(
        self,
        incident: Incident,
        *,
        initial_query_ids: Sequence[str] = (),
        evidence: Sequence[Evidence] = (),
        generation_only: bool = False,
    ) -> Investigation:
        """Run one isolated investigation; initial queries count against the same hard budget."""
        graph = self.graph.scope(
            incident.affected_entities,
            hops=self.budget.graph_hops,
            max_entities=self.budget.max_entities,
        )
        ids = {entity.id for entity in graph.entities}
        context = IncidentContext(
            incident=incident,
            graph=graph,
            queries=tuple(query for query in self.queries if query.entity_id in ids),
            evidence=tuple(evidence),
        )
        # Redact every string/metadata field, not just free-text symptoms. This exact context
        # is also retained in the report, so the public trace is not a raw-secret dump.
        context = redact_context(context)
        self._check_size(context)
        scoped_queries = {query.id for query in context.queries}
        catalog = {query.id: query for query in self.queries if query.id in scoped_queries}
        if not set(initial_query_ids) <= catalog.keys():
            raise ValueError("initial query is outside incident scope or unregistered")
        trace: list[TraceStep] = []
        tried: set[str] = set()
        candidates: dict[str, Hypothesis] = {}
        origins: dict[str, list[str]] = {}
        assessments: tuple[HypothesisAssessment, ...] = ()
        stop: StopReason = "no_candidates"
        try:
            async with asyncio.timeout(self.budget.total_timeout_seconds):
                for query_id in dict.fromkeys(initial_query_ids):
                    if len(tried) >= self.budget.max_queries:
                        break
                    context = await self._collect(catalog[query_id], context, (), tried, trace)
                for source in self.sources:
                    try:
                        async with asyncio.timeout(self.budget.source_timeout_seconds):
                            proposed = await source.propose(context.model_copy(deep=True))
                        # Bound source output before iterating it. A generator/list is not the
                        # port's return type and cannot stream forever into the registry.
                        if not isinstance(proposed, tuple) or len(proposed) > 50:
                            raise ValueError("source exceeded candidate bound")
                        # Judge candidates individually: one invalid candidate no longer
                        # discards the source's valid ones. Each rejection is traced.
                        rejections = list(getattr(source, "rejections", ()))
                        valid = []
                        for index, candidate in enumerate(proposed):
                            try:
                                checked = Hypothesis.model_validate(candidate.model_dump())
                                validate_hypothesis(checked, context)
                            except ValueError as exc:
                                rejections.append(f"candidate {index + 1}: {rejection_reason(exc)}")
                                continue
                            valid.append(checked)
                        for reason in rejections[:10]:
                            trace.append(
                                TraceStep(
                                    kind="source",
                                    reference=source.name,
                                    reason=reason,
                                    status="rejected",
                                )
                            )
                        for candidate in valid:
                            fingerprint = self._fingerprint(candidate)
                            if fingerprint in candidates:
                                origins[fingerprint].append(source.name)
                            elif len(candidates) < self.budget.max_hypotheses:
                                canonical = candidate.model_copy(
                                    update={"id": "h-" + fingerprint[:16]}
                                )
                                candidates[fingerprint] = canonical
                                origins[fingerprint] = [source.name]
                        trace.append(
                            TraceStep(
                                kind="source",
                                reference=source.name,
                                reason="validated candidates",
                                hypothesis_ids=tuple(
                                    candidate.id for candidate in candidates.values()
                                ),
                            )
                        )
                    except TimeoutError:
                        trace.append(
                            TraceStep(
                                kind="source",
                                reference=source.name,
                                reason="source deadline exceeded",
                                status="timeout",
                            )
                        )
                    except Exception:
                        # Do not leak exceptions containing credentials, URLs, or raw model text.
                        trace.append(
                            TraceStep(
                                kind="source",
                                reference=source.name,
                                reason="source rejected or unavailable",
                                status="rejected",
                            )
                        )
                while candidates:
                    assessments = tuple(
                        assess(candidate, context, tuple(origins[key]))
                        for key, candidate in candidates.items()
                    )
                    if generation_only:
                        stop = "generation_only"
                        break
                    viable = tuple(item for item in assessments if item.state != "contradicted")
                    if viable and all(item.state == "supported" for item in viable):
                        stop = "supported_candidates"
                        break
                    if len(tried) >= self.budget.max_queries:
                        stop = "budget_exhausted"
                        break
                    ranked: list[tuple[int, str, tuple[str, ...]]] = []
                    for query in context.queries:
                        if query.id in tried:
                            continue
                        targets = tuple(
                            item.hypothesis.id
                            for item in viable
                            if any(
                                (check.entity_id, check.key) == (query.entity_id, query.key)
                                for check in item.missing_checks
                            )
                        )
                        if targets:
                            ranked.append((-len(targets), query.id, targets))
                    if not ranked:
                        stop = "no_discriminating_query"
                        break
                    _, query_id, targets = min(ranked)
                    context = await self._collect(catalog[query_id], context, targets, tried, trace)
        except TimeoutError:
            stop = "deadline_exceeded"
        # Re-evaluate after timeout too: the report must retain all successfully acquired facts.
        assessments = tuple(
            assess(candidate, context, tuple(origins[key])) for key, candidate in candidates.items()
        )
        trace.append(TraceStep(kind="stop", reference=stop, reason=stop.replace("_", " ")))
        return Investigation(
            sdk_version=__version__,
            context=context,
            assessments=assessments,
            trace=tuple(trace),
            outcome=(
                "hypotheses_ready"
                if stop == "generation_only"
                else "supported"
                if stop == "supported_candidates"
                else "abstained"
            ),
            stop_reason=stop,
        )

    def _check_size(self, context: IncidentContext) -> None:
        if len(context.model_dump_json()) > self.budget.max_context_characters:
            raise ValueError("incident context exceeds character budget")

    @staticmethod
    def _fingerprint(candidate: Hypothesis) -> str:
        payload = candidate.model_dump(mode="json", exclude={"id"})
        payload["statement"] = " ".join(candidate.statement.casefold().split())
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    async def _collect(
        self,
        query: EvidenceQuery,
        context: IncidentContext,
        targets: tuple[str, ...],
        tried: set[str],
        trace: list[TraceStep],
    ) -> IncidentContext:
        tried.add(query.id)
        try:
            async with asyncio.timeout(self.budget.query_timeout_seconds):
                items = await self.connectors[query.provider].collect(query, context.incident)
            if not isinstance(items, tuple) or len(items) > 100:
                raise ValueError("connector exceeded observation bound")
            if any(item.query_id != query.id for item in items):
                raise ValueError("connector returned evidence for another query")
            candidate_context = redact_context(
                IncidentContext(
                    incident=context.incident,
                    graph=context.graph,
                    queries=context.queries,
                    evidence=(*context.evidence, *items),
                )
            )
            self._check_size(candidate_context)
            trace.append(
                TraceStep(
                    kind="query",
                    reference=query.id,
                    reason="cover unresolved checks" if targets else "initial evidence",
                    hypothesis_ids=targets,
                )
            )
            return candidate_context
        except TimeoutError:
            status: Literal["timeout", "error"] = "timeout"
        except asyncio.CancelledError:
            trace.append(
                TraceStep(
                    kind="query",
                    reference=query.id,
                    reason="investigation cancelled or deadline",
                    hypothesis_ids=targets,
                    status="timeout",
                )
            )
            raise
        except Exception:
            status = "error"
        trace.append(
            TraceStep(
                kind="query",
                reference=query.id,
                reason="no usable observation",
                hypothesis_ids=targets,
                status=status,
            )
        )
        return context
