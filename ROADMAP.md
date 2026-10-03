# Operational-intelligence roadmap

Lumis is an independent, experimental SDK. Applications integrate the framework; they do not
control its development schedule. Target release: `0.1.0` (pre-1.0). Old sprints are superseded
and preserved on the [legacy branch](https://github.com/soloshun/lumis-sdk/tree/legacy/pre-operational-intelligence-2026-10-02).

## Phase A — standalone read-only foundation

Goal: inspect an operational estate and test falsifiable explanations without action authority.

- **OI-0: clean architecture reset.** Retain only current graph/evidence/reasoning contracts;
  remove old framework, cookbook and plugin surfaces; fresh CLI/YAML/API docs.
- **OI-1: independently verifiable kernel.** Scoped topology; interchangeable rule/memory/model
  candidates; bounded observation acquisition; deterministic assessments and abstention;
  audit persistence; Kubernetes/OTLP/Prometheus and optional OpenRouter/OpenAI/Anthropic/Gemini.
- Exit: independent tests and clean-wheel CLI pass on supported Python; docs reflect actual
  shipped interfaces and mock-vs-live limitations. SDK work does not wait for GridCast.
- Status: implemented in development; publication and live consumer qualification are separate.

## Phase B — evidence depth and extensibility

Goal: improve reusable external observations and bounded investigation, not add product coupling.

- **OI-2: connector contracts and identity enrichment.** Capability/readiness reporting,
  stable external identity mapping, standardized query provenance and adapter contract kit.
  Prioritize a Git/recent-change adapter and another externally justified integration.
- **OI-3: stronger seek loop and evaluation.** Query selection baselines, explicit uncertainty,
  multi-source contradictions, budget/performance measurements and withheld-evidence scenarios.
  Evaluate proposed hypotheses against synthetic/public incident corpora.
- Exit: two independent integrations or reproducible contract fixtures, documented operational
  limits, no hidden ground-truth access, and comparable measured baselines.
- Status: planned; starts from SDK contracts, not consumer project completion.

## Phase C — reusable memory and controlled learning

Goal: reuse prior incidents without mistaking repetition for truth.

- **OI-4: retrieval and precedent.** Versioned investigation retrieval, provenance, tenant/context
  separation, invalidation and revalidation of retrieved candidates.
- **OI-5: incident-to-rule promotion.** Candidate patterns from repeated incidents; explicit minimum
  examples, evidence/quality requirements, falsifier review, human approval, versioning and rollback.
  “Happened five times” alone is insufficient to create a trusted deterministic rule.
- Exit: promotion/withdrawal tests, contradictory recurrence checks, reproducible quality and
  cost measurements; no automatic operational authority.
- Status: planned.

## Phase D — independently governed proposals and verification

Goal: introduce safe proposal boundaries only after diagnosis has measurable quality.

- **OI-6: typed proposals and independent policy.** Allow/deny scopes, risk, human approval,
  immutable decision record and authority separated from model/source confidence.
- **OI-7: bounded verification and artifact qualification.** Explicit success/failure/inconclusive
  criteria, before/after evidence, reproducible experiment package and rollback contracts.
  A real executor requires a separate approved threat-model/design review.
- Exit: independent policy cannot be bypassed by model output; replayable verification evidence;
  clear research/production boundary. Consider 1.0 only after explicit API/release review.
- Status: planned; not an executor commitment.

## Documentation and external examples in every sprint

Every sprint updates architecture decisions, Python API, CLI/YAML, schemas, migration/release
notes, safety limits and verification instructions. Add cookbook scenarios in the separate
Lumis cookbooks project, not in core. Written equivalents accompany future demonstration videos.

GridCast is the first external consumer qualification track. Its telemetry/live-model evidence
can inform priorities and reveal bugs, but is not a gate for framework implementation.
Future connectors, providers and language clients are incremental, evidence-led work, not claims
of current support. Issues/project board should preserve this SDK/consumer distinction.
