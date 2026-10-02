# Operational-intelligence architecture

Experimental reset, 2026-10-02. Active implementation path; the old architecture remains a
compatibility/control substrate. The SDK is independently usable; Lumis Engine/Control Plane
may consume it. This repository does not implement enterprise identity, billing or fleet UI.

## The first vertical slice

```text
external estate → discovered + declared graph → incident-scoped context
                                             ↓
                           rules / precedents / structured model
                                             ↓
                           validated, deduplicated hypothesis registry
                                             ↓
                           budgeted registered evidence queries
                                             ↓
                      deterministic support / contradiction / unknown
                                             ↓
                        supported candidates OR useful abstention
                                             ↓
                          serialized graph, evidence, trace, record
```

LLMs propose testable candidates, never facts, confirmation or execution authority. All sources
return `core.Hypothesis` through `reasoning.HypothesisSource`. The retained legacy
`domain.Hypothesis` is a different contract and is not used by this runtime.

## Responsibilities and dependencies

| Package | Responsibility | Dependencies |
| --- | --- | --- |
| `core` | Strict operational contracts and reference validation | Python/Pydantic |
| `graph` | Indexed traversal, bounded incident neighborhood | `core`, standard library |
| `reasoning` | Uniform source port and mechanical fact checks | `core`, standard library |
| `connectors` | Snapshot, Kubernetes, OTLP/JSON, Prometheus | `core`; HTTP only where required |
| `models` | Structured optional model provider | `core`, redaction, optional HTTP |
| `runtime` | Query/source limits, registry, terminal record, local store | Graph, source/connector ports |
| `cli` | Explicit provider composition | Above packages; lazy optional imports |

The layout follows the new design's responsibilities without renaming released imports into
incompatible types. No provider SDK is imported by core. HTTP is an optional `http` extra.

## Decisions

**An indexed adjacency graph, not a graph service.** The current need is bounded traversal,
not advanced graph algorithms. Standard-library adjacency indexes avoid another core dependency;
Pydantic snapshots provide the inspectable value. A backend may replace traversal behind this
surface once measured scale requires it. Cycles are handled. Overflow fails explicitly; it never
silently excludes a causal-path entity. Traversal is bounded by hops/entities, while extracting
edges scans the snapshot once. Graph initialization is O(V+E).

**Declared plus discovered.** Kubernetes resources have namespace/kind/name identities. OTLP
services use namespace/name identities. They are not automatically equated. Operators must bind
them explicitly where needed. Conflicting identity/attributes fail during merge; discovery does
not overwrite ownership/business metadata. Parent-span joins indicate observed dependency flow,
not causality. Upstream/downstream traverse directed edges; their operational meaning depends on
the declared relationship semantics. The incident neighborhood traverses both directions.

**A typed observation catalog.** Every query has an operator-owned ID, provider, target, key and
description. Private provider parameters stay out of model context/reports. Models select only
registered IDs. Facts must match the query target/key, lie in the incident window, have unique
IDs and stay inside byte/character/time budgets. Degraded observations cannot support a check.
Initial evidence queries consume the same budget as active queries.

**Falsifiable candidates.** Nonempty statement, causal path, predictions, evidence requests and
falsifiers are required. Graph IDs and check/query coverage are validated by the registry.
Causal-path *nodes* must exist; correctness/connectivity of the proposed path is a research
evaluation question, not inferred proof. Equivalent normalized statement/path/check records are
deduplicated with source provenance retained. This is exact semantic-record deduplication, not
embedding-based paraphrase detection.

**Mechanical assessment.** A prediction must pass; a falsifier must fail. A failed prediction or
true falsifier contradicts a candidate. Missing, degraded, type-incompatible or conflicting
observations produce unresolved checks. Contradiction dominates support. These checks are neither
formal causal inference nor calibrated confidence. Several candidates may remain supported; the
report does not silently choose a confirmed root cause.

**Explainable acquisition baseline.** Choose the untried query covering unresolved checks for
the largest number of viable candidates, breaking ties by query ID. The trace names affected
hypotheses and stop reason. This is coverage, not information-gain estimation. A failing query
is not repeatedly retried until the budget is consumed. Source failures are isolated and do not
leak raw exceptions/provider credentials into reports.

**Abstention is useful.** No candidates, missing discriminating queries, query-budget exhaustion,
or total deadline yields an ordinary investigation retaining the scoped graph, hypotheses,
missing checks, collected evidence and trace. `supported` still means unconfirmed evidence
support. `hypotheses_ready` is generation-only output. No terminal state executes an action.

## Control substrate retained

Existing proposal/approval/verification contracts stay independent. The new runtime has no action
planner/executor. Future recommendation integration cannot let a high-confidence diagnosis reduce
approval requirements. Successful command execution must not become verification success.
Recurrence learning remains future work; five repetitions is an example threshold, not truth.

## Research evidence boundary

The bundled GridCast replay and mocked transport tests establish schema/control behavior only.
They do not establish live estate diagnosis, root-cause accuracy, model quality or superiority.
The research benchmark requires independent fault injection, ground truth hidden from the
reasoning path, budget-matched baselines and measured outcomes. SEAMS paper changes/evaluation
results belong to the paper repository; this refactor does not rewrite those results.

## Source decisions

Reviewed the maintainer's local `new_design_pattern.md`, the September 2026 Lumis Product & SDK
Strategy, Local Reference System & PoC, Research/SEAMS alignment and operating roadmap under
Apeiron/Businesses/Lumis, plus the paper's SDK requirement notes. The design pattern makes the
initial milestone read-only; broader recovery/company plans remain later phases. Private business,
funding and unpublished paper material is not copied into this public repository.

External formats follow [Kubernetes get](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/),
[OTLP JSON](https://opentelemetry.io/docs/specs/otlp/),
[Prometheus HTTP API](https://prometheus.io/docs/prometheus/latest/querying/api/), and
[OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs).
