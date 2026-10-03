"""Two tool families, backed by an operator-owned catalog and shared attempt/query budgets."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from lumis_sdk.connectors.code import CodeSnapshot
from lumis_sdk.core import Evidence, EvidenceQuery, Hypothesis, IncidentContext, InvestigationBudget
from lumis_sdk.core.contracts import validate_hypothesis
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.investigation.config import InvestigatorSettings
from lumis_sdk.investigation.contracts import InspectRequest, ProbeSpec, RunMetrics, ToolReceipt
from lumis_sdk.runtime.investigation import EvidenceConnector
from lumis_sdk.sandbox.runner import ProbeRunner, code_digest
from lumis_sdk.security.operational import redact_context
from lumis_sdk.security.redaction import redact_text


class ToolBudgetExceeded(ValueError):
    pass


class InvestigationTools:
    """Per-run state. A model cannot register queries, filesystem roots or arbitrary commands."""

    def __init__(
        self,
        context: IncidentContext,
        *,
        queries: tuple[EvidenceQuery, ...],
        connectors: Mapping[str, EvidenceConnector],
        settings: InvestigatorSettings,
        budget: InvestigationBudget,
        base: Path,
        runner: ProbeRunner | None = None,
    ) -> None:
        self.context = redact_context(context)
        self.catalog = {
            query.id: query
            for query in queries
            if query.id in {item.id for item in context.queries}
        }
        self.connectors = dict(connectors)
        self.settings, self.budget, self.base, self.runner = settings, budget, base, runner
        self.receipts: list[ToolReceipt] = []
        self.candidates: dict[str, Hypothesis] = {}
        self.tried: set[str] = set()
        self.attempts = self.probes = self.output_characters = 0
        self.model_usage: dict[str, int] = {}
        self.snapshots: dict[str, CodeSnapshot] = {}
        self._lock = asyncio.Lock()
        self._check_context(self.context)

    def _check_context(self, context: IncidentContext) -> None:
        if len(context.model_dump_json()) > self.budget.max_context_characters:
            raise ValueError("incident context exceeds character budget")

    def _attempt(self) -> None:
        if self.attempts >= self.settings.budget.tool_calls_limit:
            raise ToolBudgetExceeded("tool attempt budget exhausted")
        self.attempts += 1

    def _receipt(
        self,
        operation: str,
        purpose: str,
        output: str,
        *,
        status: str = "ok",
        hypothesis_id: str | None = None,
        code_hash: str | None = None,
        snapshot_hash: str | None = None,
    ) -> ToolReceipt:
        # git.log is validated fixed-format structural SHAs/timestamps, not commit messages.
        safe = output if operation == "git.log" else redact_text(output)
        digest = hashlib.sha256(safe.encode()).hexdigest()
        remaining = max(0, self.settings.budget.max_total_tool_characters - self.output_characters)
        bound = min(self.settings.budget.max_tool_characters, remaining)
        if len(safe) > bound:
            safe = safe[: max(0, bound - 16)] + " [truncated]" if bound >= 16 else ""
        self.output_characters += len(safe)
        receipt = ToolReceipt.model_validate(
            {
                "id": f"tool-{len(self.receipts) + 1}",
                "operation": operation,
                "status": status,
                "purpose": redact_text(purpose),
                "output": safe,
                "digest": digest,
                "hypothesis_id": hypothesis_id,
                "code_digest": code_hash,
                "snapshot_digest": snapshot_hash,
            }
        )
        self.receipts.append(receipt)
        return receipt

    def metrics(self, **usage: int) -> RunMetrics:
        return RunMetrics(
            tool_attempts=self.attempts,
            evidence_queries=len(self.tried),
            probes=self.probes,
            **(self.model_usage | usage),
        )

    def _snapshot(self, repository_id: str | None) -> CodeSnapshot:
        repository = next(
            (repo for repo in self.settings.repositories if repo.id == repository_id), None
        )
        ids = {entity.id for entity in self.context.graph.entities}
        if repository is None or not set(repository.entity_ids) <= ids:
            raise ValueError("repository is unregistered or outside incident scope")
        if repository.id not in self.snapshots:
            self.snapshots[repository.id] = CodeSnapshot(repository, self.base)
        return self.snapshots[repository.id]

    def register(self, hypothesis: Hypothesis) -> None:
        payload = hypothesis.model_dump()
        payload["statement"] = redact_text(hypothesis.statement)
        candidate = Hypothesis.model_validate(payload)
        validate_hypothesis(candidate, self.context)
        previous = self.candidates.get(candidate.id)
        if previous is not None and previous != candidate:
            raise ValueError(
                "revised hypothesis requires a new ID; existing probe bindings are immutable"
            )
        if previous is None and len(self.candidates) >= self.budget.max_hypotheses:
            raise ValueError("hypothesis budget exhausted")
        self.candidates[candidate.id] = candidate

    async def collect(self, query_id: str) -> ToolReceipt:
        """Internal triage calls share the query budget but do not spend agent tool attempts."""
        query = self.catalog.get(query_id)
        if query is None or query.provider == "probe":
            return self._receipt(
                "evidence",
                "Registered observation query",
                "Query unavailable or requires probe",
                status="denied",
            )
        if query_id in self.tried:
            cached_facts = [
                item.model_dump(mode="json")
                for item in self.context.evidence
                if item.query_id == query_id
            ]
            return self._receipt("evidence", query.description, json.dumps(cached_facts))
        if len(self.tried) >= self.budget.max_queries:
            return self._receipt(
                "evidence", query.description, "Evidence query budget exhausted", status="denied"
            )
        self.tried.add(query_id)
        try:
            async with asyncio.timeout(self.budget.query_timeout_seconds):
                facts = await self.connectors[query.provider].collect(query, self.context.incident)
            if (
                not isinstance(facts, tuple)
                or len(facts) > 100
                or any(item.query_id != query.id for item in facts)
            ):
                raise ValueError("invalid connector batch")
            context = redact_context(
                IncidentContext(
                    incident=self.context.incident,
                    graph=self.context.graph,
                    queries=self.context.queries,
                    evidence=(*self.context.evidence, *facts),
                )
            )
            self._check_context(context)
            self.context = context
            return self._receipt(
                "evidence",
                query.description,
                json.dumps(
                    [
                        item.model_dump(mode="json")
                        for item in context.evidence
                        if item.query_id == query.id
                    ]
                ),
            )
        except TimeoutError:
            return self._receipt(
                "evidence", query.description, "Observation deadline exceeded", status="timeout"
            )
        except Exception:
            return self._receipt(
                "evidence", query.description, "No usable observation", status="error"
            )

    async def inspect(self, request: InspectRequest) -> ToolReceipt:
        async with self._lock:
            self._attempt()
            try:
                return await self._inspect(request)
            except TimeoutError:
                return self._receipt(
                    request.operation,
                    "Read-only inspection",
                    "Inspection deadline exceeded",
                    status="timeout",
                )
            except Exception:
                return self._receipt(
                    request.operation,
                    "Read-only inspection",
                    "Inspection denied, unavailable or invalid",
                    status="denied",
                )

    async def _inspect(self, request: InspectRequest) -> ToolReceipt:
        if request.operation == "catalog":
            ids = {entity.id for entity in self.context.graph.entities}
            catalog: dict[str, Any] = {
                "operations": ["catalog", "graph", "evidence", "hypothesis.register"],
                "queries": [query.model_dump(mode="json") for query in self.context.queries],
                "repositories": [
                    {"id": repo.id, "files": repo.files}
                    for repo in self.settings.repositories
                    if set(repo.entity_ids) <= ids
                ],
                "probe_enabled": self.runner is not None,
            }
            if catalog["repositories"]:
                catalog["operations"] += ["code.read", "code.search", "git.log", "git.diff"]
            return self._receipt("catalog", "Available bounded tools", json.dumps(catalog))
        if request.operation == "evidence" and request.query_id:
            return await self.collect(request.query_id)
        if request.operation == "hypothesis.register" and request.hypothesis:
            self.register(request.hypothesis)
            return self._receipt(
                request.operation,
                "Register a falsifiable candidate",
                request.hypothesis.model_dump_json(),
            )
        if request.operation == "graph" and request.target:
            graph = OperationalGraph(self.context.graph).dependencies_within(
                request.target, hops=1, max_entities=self.budget.max_entities
            )
            return self._receipt("graph", "Incident neighborhood", graph.model_dump_json())
        snapshot = self._snapshot(request.target)
        if request.operation == "code.read" and request.path:
            output = snapshot.read(request.path)
        elif request.operation == "code.search" and request.text:
            output = snapshot.search(request.text)
        elif request.operation in {"git.log", "git.diff"}:
            output = await snapshot.git(
                request.operation,
                since=self.context.incident.started_at.isoformat(),
                until=self.context.incident.ended_at.isoformat(),
                base_commit=request.base_commit,
                head_commit=request.head_commit,
            )
        else:
            raise ValueError("invalid tool request")
        return self._receipt(
            request.operation,
            "Allowlisted repository inspection",
            output,
            snapshot_hash=snapshot.digest,
        )

    async def probe(self, spec: ProbeSpec) -> ToolReceipt:
        async with self._lock:
            self._attempt()
            code_hash = code_digest(spec)
            snapshot_hash = None
            try:
                candidate = self.candidates.get(spec.hypothesis_id)
                query = self.catalog.get(spec.query_id)
                if (
                    candidate is None
                    or query is None
                    or query.provider != "probe"
                    or query.id not in candidate.evidence_needed
                ):
                    raise ValueError(
                        "probe requires a registered candidate and its operator-owned probe query"
                    )
                if (
                    self.runner is None
                    or self.probes >= self.settings.budget.max_probes
                    or query.id in self.tried
                    or len(self.tried) >= self.budget.max_queries
                ):
                    raise ValueError("probe disabled, reused or over budget")
                files: dict[str, str] = {}
                if spec.repository is not None:
                    snapshot = self._snapshot(spec.repository)
                    files = dict(snapshot.files)
                    snapshot_hash = snapshot.digest
                self.probes += 1
                self.tried.add(query.id)
                async with asyncio.timeout(self.budget.query_timeout_seconds):
                    value = await self.runner.run(spec, files)
                fact = Evidence(
                    id=f"probe-{self.probes}",
                    query_id=query.id,
                    entity_id=query.entity_id,
                    key=query.key,
                    value=value,
                    observed_at=self.context.incident.ended_at,
                    source="synthetic-sandbox-experiment",
                    retrieval_method="isolated-diagnostic-probe",
                    quality="degraded",
                )
                context = redact_context(
                    IncidentContext(
                        incident=self.context.incident,
                        graph=self.context.graph,
                        queries=self.context.queries,
                        evidence=(*self.context.evidence, fact),
                    )
                )
                self._check_context(context)
                self.context = context
                return self._receipt(
                    "probe",
                    spec.purpose,
                    fact.model_dump_json(),
                    hypothesis_id=spec.hypothesis_id,
                    code_hash=code_hash,
                    snapshot_hash=snapshot_hash,
                )
            except TimeoutError:
                return self._receipt(
                    "probe",
                    spec.purpose,
                    "Probe deadline exceeded",
                    status="timeout",
                    hypothesis_id=spec.hypothesis_id,
                    code_hash=code_hash,
                    snapshot_hash=snapshot_hash,
                )
            except Exception:
                return self._receipt(
                    "probe",
                    spec.purpose,
                    "Probe denied, unavailable or invalid",
                    status="denied",
                    hypothesis_id=spec.hypothesis_id,
                    code_hash=code_hash,
                    snapshot_hash=snapshot_hash,
                )
