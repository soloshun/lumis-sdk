# Operational-intelligence roadmap

Lumis is an independent, experimental SDK. Applications integrate the framework; they do not
control its development schedule. Target release: `0.1.0` (pre-1.0). Old sprints are superseded
and preserved on the [legacy branch](https://github.com/soloshun/lumis-sdk/tree/legacy/pre-operational-intelligence-2026-10-02).

Checked items mean implemented and independently tested in the `dev` architecture, **not**
published or production-qualified. Unchecked items remain required work, not implicit support.
Each OI milestone is a sprint-sized slice; phases may contain incremental sub-sprints.

## Phase A — standalone read-only foundation

Goal: inspect an operational estate and test falsifiable explanations without action authority.

- [x] **OI-0: clean architecture reset.** Current graph/evidence/reasoning contracts only;
  no obsolete framework, cookbooks or plugins; fresh CLI/YAML/API documentation and legacy branches.
- [x] **OI-1: independently verifiable kernel.** Scoped topology; interchangeable rule/memory/model
  candidates; bounded observation acquisition; deterministic assessment and abstention; audit store;
  scoped Kubernetes/OTLP/Prometheus and optional OpenRouter/OpenAI/Anthropic/Gemini.
- [x] Exit: independent tests and clean-wheel CLI on supported Python; accurate shipped API docs
  and mock-vs-live limits. SDK implementation does not wait for GridCast.
- [ ] Experimental `0.1.0` publication (separate qualification/release issue #9).
- [ ] Live consumer qualification (external issue #96; not an SDK implementation gate).

## Phase B — evidence depth and extensibility

Goal: improve reusable external observations and bounded investigation, not add product coupling.

- [ ] **OI-2: connector contracts and identity enrichment.**
  - [x] **OI-2a: YAML-led discovery and graph integration.** Pydantic + NetworkX multigraph;
    bounded neighborhoods/DOT export; shared Python/CLI prepare-and-investigate composition.
  - [x] Query/candidate IDs bind after enabled discovery; unresolved IDs fail before investigation.
  - [x] Per-source statuses, fail-closed partial discovery, cancellation and aggregate budgets.
  - [x] Explicit aliases, Kubernetes resource/logical-service links and external topology JSON.
  - [x] Existing Prometheus service-graph metric → topology, with explicit namespace and bounds.
  - [x] Two independent portable graph inputs, mocked HTTP contracts and runnable offline notebook.
  - [ ] **OI-2b: Git/recent-change evidence.** Typed time-bounded change records, repository/commit
    identity, safe read-only access and implemented `recent_changes_affecting` semantics.
  - [ ] Reusable adapter conformance kit: capabilities, query provenance, limits and failure cases.
  - [x] **OI-2c: data/orchestration observations.** Scoped Prefect flow/task filters and observed
    workflow/task dependency topology, independent fixtures, least privilege and documented limits.
  - [x] Loki/Tempo read-only evidence adapters with endpoint-backed registered queries and bounded
    Tempo trace discovery; authenticated YAML/runtime/agent integration and failure-case tests.
  - [ ] Live Loki/Tempo/Prefect access and evidence-quality qualification in external consumers.
- [ ] **OI-3: stronger seek loop and evaluation.** Query-selection baselines, explicit uncertainty,
  multi-source contradictions, budget/performance measurements and withheld-evidence scenarios.
  Evaluate proposed hypotheses against synthetic/public incident corpora.
- [ ] Exit: two independent integrations or reproducible contract fixtures, documented operational
  limits, no hidden ground-truth access, and comparable measured baselines.

OI-2a provides the first fixtures; the adapter kit, change evidence and measured baselines remain.
The continuation adds an explicit public artifact slice before broader evidence/learning work:

- [x] **OI-A1: evidence-backed deterministic sandwich.** Three-state findings, nonterminal
  signatures, multi-observable terminal sufficiency, ambiguity/scope checks and caller guard.
- [x] **OI-A2: basic single investigator.** Pydantic AI native providers, dynamic inspect/probe
  tool families, approved graph/query/code/Git scope, budgets, typed output and mechanical assessment.
- [x] **OI-A3: diagnostic experiments and audit.** Opt-in resource-limited Docker, copied
  source only, degraded probe evidence, receipts/digests, immutable SQLite reports/manual resolutions.
- [x] **OI-A4: usable public package surface.** CLI incident/menu/SVG, API/YAML/sandbox
  documentation, schemas and executable offline agent notebook.
- [ ] **OI-A5: artifact evaluation.** Versioned independent/live scenarios, provider qualification,
  diagnosis/abstention/cost measurements and external cookbook evidence.

OI-A1–A4 implement the basic investigation proof of concept. Advanced governance and orchestration
are not implemented yet and are deferred until after PoC evaluation.
OI-2b remains open: basic Git inspect tools do not finish typed change records.
Next is evidence/evaluation qualification or OI-2b, never automatic recovery.

## Phase C — reusable memory and controlled learning

Not implemented yet. Deferred until after the current PoC has been evaluated.

Goal: reuse prior incidents without mistaking repetition for truth.

- [ ] **OI-4: retrieval and precedent.** Versioned investigation retrieval, provenance, tenant/context
  separation, invalidation and revalidation of retrieved candidates.
- [ ] **OI-5: incident-to-rule promotion.** Candidate patterns from repeated incidents; explicit minimum
  examples, evidence/quality requirements, falsifier review, human approval, versioning and rollback.
  “Happened five times” alone is insufficient to create a trusted deterministic rule.
- [ ] Exit: promotion/withdrawal tests, contradictory recurrence checks, reproducible quality and
  cost measurements; no automatic operational authority.

## Phase D — independently governed proposals and verification

Not implemented yet. Deferred until after PoC evaluation. Only tentative diagnostic suggestions
and separate human attestations are implemented now; policy-controlled execution and recovery
are not available.

Goal: introduce safe proposal boundaries only after diagnosis has measurable quality.

- [ ] **OI-6: typed proposals and independent policy.** Allow/deny scopes, risk, human approval,
  immutable decision record and authority separated from model/source confidence.
- [ ] **OI-7: bounded verification and artifact qualification.** Explicit success/failure/inconclusive
  criteria, before/after evidence, reproducible experiment package and rollback contracts.
  A real executor requires a separate approved threat-model/design review.
- [ ] Exit: independent policy cannot be bypassed by model output; replayable verification evidence;
  clear research/production boundary. Consider 1.0 only after explicit API/release review.

These are planned capabilities, not an executor commitment.

## Cookbook integration readiness

Goal: a cookbook declares approved source/query/candidate YAML, supplies an incident, and calls
`YamlProject.from_file(...).handle_incident(...)` without application-specific runtime assembly.

- [x] Shared YAML composition; no GridCast imports or hidden ground-truth access.
- [x] Offline replay without network/model credentials or an external repository.
- [x] Bounded, inspectable operational graph and declared dataset/job lineage.
- [x] Mocked read-only Kubernetes/OTLP and Prometheus topology/evidence contracts.
- [x] API/YAML/CLI documentation and runnable notebook match the shipped interfaces.
- [x] Conservative triage, basic tool-agent contract, isolated probes and human-review audit.
- [ ] Qualify real cookbook endpoints, telemetry coverage, identities, namespaces and RBAC.
- [ ] Validate live model schema support, privacy, cost, candidate quality and missing-data behavior.
- [ ] Add/qualify remaining adapters before claiming all GridCast fault/scenario families work.

The first read-only Kubernetes/Prometheus slice is ready for **integration testing**, not a claim
that every cookbook works with arbitrary telemetry and no configuration. Missing providers are
tracked above. See [integration matrix](docs/integrations.md) and [verification](docs/verification.md).

## Documentation and external examples in every sprint

Every sprint updates architecture decisions, Python API, CLI/YAML, schemas, migration/release
notes, safety limits and verification instructions. Add cookbook scenarios in the separate
Lumis cookbooks project, not in core. Written equivalents accompany future demonstration videos.

GridCast is the first external consumer qualification track. Its telemetry/live-model evidence
can inform priorities and reveal bugs, but is not a gate for framework implementation.
Future connectors, providers and language clients are incremental, evidence-led work, not claims
of current support. Issues/project board must preserve this SDK/consumer distinction.
