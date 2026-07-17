# Phase 3 — Intelligence, memory, and integrations

Sprints: 12–17

## Phase outcome

The SDK provides explainable correlation, causal/lineage context, rule analytics, quality-aware
memory, optional semantic retrieval, semantic audit events, and a useful integration ecosystem.
Heavy or vendor-specific dependencies remain independently installable packages.

## Entry criteria

- Phase 2 evaluation and grounding contracts are available to measure new intelligence.
- Integration priorities are backed by maintainer/community/adopter demand.
- Every proposed official package has a maintainer, authority declaration, test strategy, and
  upstream API compatibility plan.

## Sprint 12 — Explainable incident correlation

**Outcome:** deterministic exact-key and bounded time-window correlation produces reversible,
feature-level explanations before probabilistic or model ranking is considered.

- [ ] Define signal, incident candidate, correlation edge, feature contribution, decision, and
      operator correction contracts.
- [ ] Add bounded exact-key/time-window scoring with stable tie-breaking and reasons.
- [ ] Represent merge, split, reject, and supersede corrections without rewriting history.
- [ ] Add replay fixtures for duplicates, bursts, clock skew, missing keys, and contradictory
      signals.
- [ ] Add optional correlation-provider plugin capability only after the core contract stabilizes.

**Acceptance evidence:** corrections replay deterministically and every decision exposes feature
contributions; model ranking cannot silently merge incidents.

## Sprint 13 — Causal and data-lineage graphs

**Outcome:** jobs, runs, datasets, services, deployments, and changes share versioned graph
contracts and bounded traversal independent of a graph database or lineage vendor.

- [ ] Define node, edge, external reference, provenance, temporal validity, and change-event types.
- [ ] Add bounded upstream/downstream/neighborhood traversal requests and results.
- [ ] Convert graph results into ordinary evidence with stable references.
- [ ] Add `LINEAGE_PROVIDER` discovery and capability negotiation.
- [ ] Build synthetic graph fixtures and reference in-memory traversal.
- [ ] Prove optional OpenLineage and dbt manifest/run-results adapters; evaluate Airflow, Dagster,
      and Prefect packages from demand rather than bundling them in core.

**Acceptance evidence:** the same graph fixture is traversed and cited consistently by the
reference adapter and at least one optional adapter.

## Sprint 14 — Rule analytics and semantic audit events

**Outcome:** immutable events explain rule behavior and lifecycle activity without remote telemetry
or hosted analytics.

- [ ] Define matched, missed, conflicted, shadow, and error rule-evaluation events with revision,
      feature facts, decision, and latency.
- [ ] Add pure reducers for coverage, shadow comparison, stale-rule signals, and explicitly named
      precision proxies.
- [ ] Define semantic events across evidence, model invocation, correlation, policy, proposal,
      external execution, verification, and learning.
- [ ] Include causation/correlation IDs, actor/automation identity, artifact hashes, and
      redaction-safe metadata.
- [ ] Add JSONL/reference report output and deterministic reducer fixtures.

**Acceptance evidence:** analytics derive entirely from immutable public events; proxy metrics are
not mislabeled as ground-truth precision.

## Sprint 15 — Memory feedback and semantic retrieval

**Outcome:** users can measure retrieval usefulness and optionally add semantic strategies without
allowing feedback or frequency to rewrite confirmed truth.

- [ ] Define useful, irrelevant, incorrect, and superseded feedback events with actor, query,
      strategy/version, result identity, and score components.
- [ ] Add offline memory-quality cases and reducers; feedback is append-only.
- [ ] Define embedding references, vector queries, score components, re-index/delete operations,
      strategy fallback, and unavailable outcomes.
- [ ] Preserve exact/full-text retrieval as the default independent baseline.
- [ ] Add optional PostgreSQL full-text and pgvector strategies with migration/benchmark guidance.
- [ ] Publish custom PostgreSQL schema, indexing, backup, and multi-process examples.

**Acceptance evidence:** confirmed truth is unchanged by feedback; optional semantic retrieval must
show measured improvement on a published corpus before becoming a recommended strategy.

## Sprint 16 — Observability and cloud evidence packages

**Outcome:** users can connect common operational signals through bounded read-only adapters and
relatable examples without enlarging core dependencies.

- [ ] Publish an Alertmanager webhook normalization and Prometheus query evidence walkthrough.
- [ ] Define OpenTelemetry log/trace/metric evidence mapping and redaction guidance.
- [ ] Evaluate official Sentry and AWS CloudWatch evidence packages with exact authority,
      pagination, timeout, cost, and response-size boundaries.
- [ ] Add S3-compatible bounded object-evidence references and retention hooks as an optional
      package, never arbitrary bucket traversal.
- [ ] Add fake transports, recorded public/synthetic fixtures, contract tests, and package support
      status for every accepted adapter.
- [ ] Produce written tutorials and maintainer-recorded video scripts for Prometheus and AWS paths.

**Acceptance evidence:** CI uses no live credential or billable API; each adapter fails closed on
scope, pagination, timeout, malformed, and oversized responses.

## Sprint 17 — Data, orchestration, and delivery packages

**Outcome:** data/ML and software-delivery users see end-to-end examples matching their actual
systems while the SDK remains framework-neutral.

- [ ] Prove demand-led adapters for OpenLineage/dbt plus at least one of Airflow, Prefect, Dagster,
      or Temporal as evidence/lifecycle integration—not a core dependency.
- [ ] Publish GitHub Actions evidence and verifier boundaries; other CI/CD adapters remain
      community/demand-led.
- [ ] Add data-quality, schema-drift, failed deployment, model-regression, and dependency-outage
      scenarios using synthetic/public artifacts.
- [ ] Document adapter composition, credential references, rate limits, support level, and
      upstream-version compatibility.
- [ ] Add an integration catalog generated from installed manifests and maintained metadata.
- [ ] Publish contributor templates for a new official/community adapter and companion tutorial.

**Acceptance evidence:** at least three domain-distinct optional paths pass reusable contracts and
offline cookbooks; no package is called official without an owner and maintenance policy.

## Optional package queue

| Area | Candidate package boundary | Planned sprint |
| --- | --- | --- |
| Agent runtime | Pydantic AI bridge; framework types remain adapter-local | Phase 2, S10 |
| Model providers | OpenRouter, OpenAI, Anthropic, generic OpenAI-compatible/Ollama | After Phase 2 contracts; demand-led |
| Lineage | OpenLineage and dbt; Airflow/Dagster/Prefect as demand supports | S13/S17 |
| Observability | Alertmanager/Prometheus, OpenTelemetry, Sentry, CloudWatch | S16 |
| Delivery | GitHub Actions evidence/verifier and later CI/CD adapters | S17 |
| Memory | PostgreSQL full text and optional pgvector strategy | S15 |
| Object evidence | S3-compatible bounded references | S16 |

## Phase 3 exit criteria

- Correlation, graph traversal, rule analytics, and memory feedback are explainable and replayable.
- Optional semantic retrieval is measured against the exact/full-text baseline.
- Multiple independently installable integration paths cover observability, data, and delivery.
- Adapter fixtures require no production credential, private data, or billable CI request.
- Package ownership/support and deprecation expectations are public.
