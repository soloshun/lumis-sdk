"""Deterministic sandwich: scope/triage, optional investigator, mechanical report, human review."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from lumis_sdk import __version__
from lumis_sdk.checks import TriageGuard, evaluate_checks, sufficient_finding
from lumis_sdk.core import Incident, IncidentContext
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.investigation.contracts import AgentOutput, Finding, IncidentReport
from lumis_sdk.investigation.tools import InvestigationTools, InvestigatorStopped
from lumis_sdk.reasoning import assess
from lumis_sdk.runtime.investigation import EvidenceConnector
from lumis_sdk.runtime.project import OperationalProject
from lumis_sdk.sandbox.runner import ProbeRunner
from lumis_sdk.security.redaction import redact_text


class Investigator(Protocol):
    async def investigate(
        self, tools: InvestigationTools, findings: tuple[Finding, ...]
    ) -> AgentOutput: ...


async def handle_incident(
    project: OperationalProject,
    graph: OperationalGraph,
    incident: Incident,
    *,
    connectors: Mapping[str, EvidenceConnector],
    base: Path,
    investigator: Investigator | None = None,
    use_agent: bool = False,
    guard: TriageGuard | None = None,
    runner: ProbeRunner | None = None,
) -> IncidentReport:
    scoped = graph.scope(
        incident.affected_entities,
        hops=project.budget.graph_hops,
        max_entities=project.budget.max_entities,
    )
    ids = {entity.id for entity in scoped.entities}
    context = IncidentContext(
        incident=incident,
        graph=scoped,
        queries=tuple(query for query in project.queries if query.entity_id in ids),
    )
    tools = InvestigationTools(
        context,
        queries=project.queries,
        connectors=connectors,
        settings=project.investigator,
        budget=project.budget,
        base=base,
        runner=runner,
    )
    rules = tuple(
        rule
        for rule in project.checks
        if set(rule.hypothesis.causal_path) <= ids
        and all(query in tools.catalog for query in rule.hypothesis.evidence_needed)
    )
    rules = tuple(
        type(rule).model_validate(
            rule.model_dump()
            | {
                "hypothesis": rule.hypothesis.model_dump()
                | {"statement": redact_text(rule.hypothesis.statement)}
            }
        )
        for rule in rules
    )
    findings: tuple[Finding, ...] = ()
    output = AgentOutput()
    route = "human"
    stop = "agent_not_enabled"
    notes: list[str] = []
    try:
        async with asyncio.timeout(project.budget.total_timeout_seconds):
            required = dict.fromkeys(
                (
                    *project.initial_query_ids,
                    *(query for rule in rules for query in rule.hypothesis.evidence_needed),
                )
            )
            if not set(required) <= tools.catalog.keys():
                raise ValueError("initial or triage query is outside incident scope")
            for query in required:
                if len(tools.tried) >= project.budget.max_queries:
                    break
                await tools.collect(query)
            findings = evaluate_checks(rules, tools.context)
            sufficient = sufficient_finding(rules, findings, tools.context, guard)
            if sufficient is not None:
                return IncidentReport(
                    sdk_version=__version__,
                    context=tools.context,
                    findings=findings,
                    assessments=(sufficient.assessment,),
                    receipts=tuple(tools.receipts),
                    route="deterministic",
                    conclusion="supported_diagnosis",
                    stop_reason="sufficient_terminal_signature",
                    metrics=tools.metrics(),
                )
            try:
                if investigator is not None:
                    route = "agent"
                    output = await investigator.investigate(tools, findings)
                    stop = "agent_completed"
                elif use_agent:
                    route = "agent"
                    if project.models is None:
                        raise ValueError("explicit model configuration required")
                    from lumis_sdk.investigation.providers import configured_investigator

                    async with configured_investigator(
                        project.models,
                        timeout=project.budget.source_timeout_seconds,
                        retries=project.investigator.budget.validation_retries,
                    ) as agent:
                        output = await agent.investigate(tools, findings)
                    stop = "agent_completed"
            except InvestigatorStopped as exc:
                # Budget exhausted or the model could not produce valid output: keep what the run
                # registered and collected; no final answer means no suggestions.
                stop = exc.stop_reason
                notes.append(f"Investigator stopped before a final answer ({stop}): {exc}")
            payload = output.model_dump()
            for hypothesis in payload["hypotheses"]:
                hypothesis["statement"] = redact_text(hypothesis["statement"])
            for suggestion in payload["suggestions"]:
                suggestion["description"] = redact_text(suggestion["description"])
                if suggestion["patch"] is not None:
                    suggestion["patch"] = redact_text(suggestion["patch"])
            payload["unresolved_questions"] = [
                redact_text(question) for question in payload["unresolved_questions"]
            ]
            output = AgentOutput.model_validate(payload)
            # Accept per candidate: an invalid hypothesis (and suggestions that depend on it) is
            # dropped with its reason; valid candidates and suggestions are kept.
            for candidate in output.hypotheses:
                try:
                    tools.register(candidate)
                except ValueError as exc:
                    notes.append(f"Lumis rejected candidate {candidate.id}: {exc}")
            accepted = set(tools.candidates)
            kept = []
            for suggestion in output.suggestions:
                problem = tools.suggestion_problem(suggestion, accepted)
                if problem is None:
                    kept.append(suggestion)
                else:
                    notes.append(f"Lumis rejected a suggestion: {problem}")
            output = output.model_copy(update={"suggestions": tuple(kept)})
            # Validate evidence independently of the agent's narrative; optionally fill requested
            # operator-owned checks under the same remaining query budget. Never execute a fix.
            for candidate in tuple(tools.candidates.values()):
                for query in candidate.evidence_needed:
                    if len(tools.tried) >= project.budget.max_queries:
                        break
                    if query not in tools.tried and tools.catalog[query].provider != "probe":
                        await tools.collect(query)
    except TimeoutError:
        stop = "deadline_exceeded"
    except Exception:
        stop = "investigator_rejected_or_unavailable"
        output = AgentOutput()  # no unvalidated suggestions; retain already registered candidates
    if not findings:
        findings = evaluate_checks(rules, tools.context)
    assessments = tuple(
        assess(candidate, tools.context, ("agent",)) for candidate in tools.candidates.values()
    )
    viable = tuple(item for item in assessments if item.state != "contradicted")
    supported = bool(viable) and all(item.state == "supported" for item in viable)
    return IncidentReport.model_validate(
        {
            "sdk_version": __version__,
            "context": tools.context,
            "findings": findings,
            "assessments": assessments,
            "receipts": tuple(tools.receipts),
            "suggestions": output.suggestions,
            "unresolved_questions": (
                *output.unresolved_questions,
                *(redact_text(note)[:4000] for note in notes),
            ),
            "route": route,
            "conclusion": "supported_diagnosis"
            if supported and stop == "agent_completed"
            else "requires_human_expert"
            if route == "human"
            else "insufficient_evidence",
            "stop_reason": stop,
            "metrics": tools.metrics(),
        }
    )
