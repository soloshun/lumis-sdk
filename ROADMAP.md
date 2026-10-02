# Lumis SDK operational-intelligence roadmap

Updated 2026-10-02. Experimental, research-driven Python SDK. Data & AI infrastructure is the
first wedge. GridCast is the synthetic reference estate, not a customer or energy-grid
deployment. **LLM proposes; Lumis tests against evidence.** Support is not causal proof.

## Reset and preservation

The [July roadmap](docs/legacy/2026-07-roadmap.md) and old Phase 1–4 plans are historical.
Completed work stays credited. Unfinished legacy Sprints 6–23 are superseded, not completed.
New sprints use `OI-*` identifiers. The exact pre-reset code is preserved remotely on
`legacy/pre-operational-intelligence-2026-10-02` at `8a371d1`.

Existing `domain`, `application`, `ports`, `adapters`, and v1 configuration APIs remain usable
for released consumers and paper regression experiments. New APIs use `core`, `graph`,
`connectors`, `reasoning`, `models`, and `runtime`. Removal requires migration and adoption
review. The new wire version is `lumis.dev/operational-v1alpha1`; old v1 documents retain meaning.
Legacy cookbooks remain as tested compatibility examples; GridCast is the active example track.

## Phases

| Phase | Goal | Sprints | Exit evidence |
| --- | --- | --- | --- |
| A — read-only foundation | External connection, scoped graph, falsifiable candidates | OI-0–1 | Offline conformance plus live GridCast incident run |
| B — benchmark and diagnosis | Measure evidence-seeking value against simpler approaches | OI-2–3 | Repeatable corpus, baselines, abstention and evidence-efficiency results |
| C — guarded recovery | Earn recommendation and controlled-lab actuation | OI-4–5 | Independent policy gate, bounded executor, post-action verification |
| D — adoption and learning | Usability, reviewed reuse, qualified 0.1.0 release | OI-6–7 | External walkthrough, trajectory controls, release evidence |
| E — evidence-led extension | Extend only when a measured incident needs it | OI-8 onward | Accepted RFC and benchmark/adoption evidence |

Sprint size is outcome-driven, not a calendar commitment.

## Phase A: read-only foundation

### OI-0 — reset and contracts

Deliver: architecture decision, legacy snapshot, honest research-status labels, strict schemas for
entities/relationships, incident windows, observations/provenance, queries, falsifiable hypotheses,
budgets, terminal investigation and audit trace. Preserve independent policy/verification.

Acceptance: reject empty falsifiers, unknown fields, stale facts, orphan relationships and invalid
references. Preserve old tests/paper imports; check generated schemas in CI.
Status: complete; merged through [PR #93](https://github.com/soloshun/lumis-sdk/pull/93)
at `ad01fda`, with all ten PR checks passing and the retained paper regression unchanged.

### OI-1 — external GridCast slice

Deliver: declared/discovered topology merge, indexed bounded traversal, namespace-scoped Kubernetes
discovery, OTLP/JSON topology import, Prometheus read adapter, uniform rule/memory/model source port,
optional structured OpenRouter generation, offline CLI example, budgeted evidence-query selection,
mechanical support/contradiction and persisted abstention. No executor.

Acceptance: independently running GridCast supplies topology/observations through public ports;
produce 3–5 falsifiable model candidates, inspect scoped graph and query trace, replay withheld
evidence. Estate application services must not import Lumis or reveal injected fault labels.
Status: SDK/offline/transport slice merged through PR #93. Live GridCast and actual model evidence
remain open in [#92](https://github.com/soloshun/lumis-sdk/issues/92); this sprint is not complete.

## Phase B: benchmark and diagnosis

### OI-2 — benchmark before platform

Deliver 8–15 reproducible independent incident fixtures: query amplification, stale upstream data,
credential/configuration failure, resource pressure, model slowdown, compound/irrelevant concurrent
changes. Keep ground truth out of runtime inputs; separate development and held-out incidents.

Compare rule/runbook, single-pass LLM, tool-using LLM without hypothesis management, and Lumis using
equal observation surfaces/budgets. Define top-k recall, causal-path match, unsupported claims,
abstention in both directions, query count, time, tokens/cost and deterministic replay metrics.
Pin dependencies and include negative findings.

Acceptance: clean reproduction with label definitions and hidden ground truth. Contract tests are
not a comparative research benchmark. No superiority claim before experimental evidence.
Status: planned.

### OI-3 — evidence-seeking diagnosis

Deliver query policies justified by OI-2, candidate revision, explicit uncertainty, deployment/Git
and Prefect adapters needed by actual incidents, historical graph/change context, source ablations.

Acceptance: measured query efficiency and false-confident diagnosis against baselines. Scores are
not called calibrated probabilities without calibration data. Missing evidence yields abstention.
Status: planned.

## Phase C: guarded recovery

### OI-4 — bounded recommendations

Bridge investigated candidates to typed allowlisted proposals with preconditions, risk,
rollback and verification plans. Abstention emits no actionable plan. Support/model confidence
cannot lower approval requirements.

Acceptance: maximum-confidence high-risk proposal remains pending; unknown actions fail closed;
each proposal pins policy and evidence. Status: planned.

### OI-5 — controlled-lab execution and verification

Deliver RFC-reviewed reversible executor, idempotency, approval revision checks, execution limits,
cancellation, audit, rollback and independently gathered post-action evidence. Check downstream
forecast freshness/completeness as well as process health. Introduce durable workflow machinery
only when restart/retry experiments require it.

Acceptance: selected injected failures recover reproducibly; failed/unknown verification never
marks resolution. No production authority is implied. Deliberately outside the initial SEAMS
control-substrate implementation. Status: planned.

## Phase D: adoption and learning

### OI-6 — external usability and documentation

Deliver clean installs, operator diagnostics, connector security review, independent engineer
walkthrough, contributor examples, version-pinned artifact runbook and written/video scripts.
Keep small offline examples here; move large GridCast cookbooks to a separate repository only
once that repository exists.

Acceptance: external engineer runs a controlled estate unaided; record feedback. Status: planned.

### OI-7 — reviewed trajectory learning and 0.1.0 qualification

Deliver episode retrieval without importing prior evidence as current truth, environment isolation,
reviewed truth transitions and recurrence-to-rule *candidate* generation from repeated verified
incidents. Frequency alone never confirms a rule; review and regression evaluation are required.
Resolve compatibility/migration for legacy APIs.

Acceptance: distribution/plugin compatibility, clean installs, threat review, reproducibility,
live GridCast and external adoption/review gates have attached records.
Target **0.1.0**, not 1.0.0. `0.1.0rc1` is a historical release candidate, not a release of this
new architecture. Qualify a new RC before final release; never overwrite a PyPI version.
Status: planned. [Reset release gates](docs/operational-intelligence/release-gates.md).

## Phase E: extension earned by evidence

OI-8 onward may cover OpenLineage, additional observability/model providers, larger graph storage,
calibration, TypeScript/wire conformance, edge/SLM constraints and simulated sensors. Each requires
a specific measured failure, dependency/authority budget and accepted RFC.

Enterprise tenancy/identity/billing/fleet/UI belong to the product. Physical actuation, large agent
taxonomies, graph/vector databases and custom foundation models are not current SDK deliverables.

## Every sprint's definition of done

1. Name the incident or research requirement that needs the component.
2. Specify types, provenance, uncertainty, authority, privacy and failure behavior.
3. Pass unit/contract, hostile-input, timeout and replay tests; record live evidence separately.
4. Update API docs, schemas, migration notes, changelog, runnable example and docs-site source queue.
5. Pin SDK/provider/testbed versions; keep ground truth hidden.
6. Branch from `dev`, PR to `dev`, wait for checks, qualify a separate release promotion.
7. Link evidence on issues/board; implementation merge does not close live/external review gates.

The original research remains the guarded-control substrate. The new hypothesis-and-evidence
architecture is experimental; this roadmap claims neither benchmark superiority nor acceptance.
