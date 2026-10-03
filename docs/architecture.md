# Standalone operational intelligence

## Responsibility

Lumis is an independent framework for testing explanations about operational incidents.
A consuming application provides telemetry and integration adapters; it is not imported into
the kernel. A specific testbed's release, deployment or cookbook cannot block SDK implementation.

The working rule is “LLM proposes; Lumis tests.” Evidence support is not formal proof,
a confirmed root cause, or permission to execute a change.

## Current flow

The recommended path is [incident investigation](incident-investigation.md): prepared context →
evidence-backed triage → sufficient signature or one bounded Pydantic AI investigator →
mechanical assessment → human review. inspect reads scoped evidence, graph and approved code/Git.
probe tests registered candidates only in an explicitly enabled resource-limited Docker container.
Its results are synthetic/degraded, not independent production proof. No fix is applied.
Human resolutions may be recorded separately.

The following lower-level investigate path remains as a candidate/evaluation baseline:

YAML project → bounded discovery + identity binding → incident + prepared graph → bounded context → rules / retrieved candidates /
optional model → validation and deduplication → registered evidence queries → deterministic
assessment → supported candidates or abstention → optional persisted investigation.

All sources use `Hypothesis`: statement, graph-referenced causal path, predictions,
evidence needed and falsifiers. A model cannot add observed evidence, ground-truth labels,
an action, confirmation state or an unrestricted tool command.

The incident includes an explicit timezone-aware observation window. The runtime validates
evidence identities, catalog association and timestamps. Conflicting, stale, missing or degraded
facts cannot silently turn into support. Contradiction takes precedence.

## Package responsibilities

| Package | Responsibility |
| --- | --- |
| `core` | Pydantic contracts and invariants |
| `graph` | NetworkX directed multigraph, identity links and bounded neighborhood traversal |
| `connectors` | Read-only external topology and observation adapters |
| `reasoning` | Interchangeable candidate sources and mechanical assessment |
| `models` | Optional model adapter, no decision or action authority |
| `checks` | Conservative triage and caller-owned sufficiency guard |
| `investigation` | Typed reports, bounded tools and optional single Pydantic AI investigator |
| `sandbox` | Resource-limited copied-source experiments; no host fallback |
| `runtime` | Shared YAML preparation/discovery, investigation loop, scaffold and SQLite records |
| `security` | Conservative model/report context redaction |
| `cli` | Explicit composition of the public contracts |

The graph uses Pydantic contracts plus NetworkX `MultiDiGraph`, as proposed in the design.
Parallel relationship kinds survive normalization. Traversal is cycle-safe and refuses
entity-budget overflow; NetworkX exports are independent deep copies. No graph database is required.
Relationship directions represent observed/declared operational relations, not proven causality.
See [graph API and lineage](graph.md). Visualization is optional; the graph primarily scopes reasoning.

## Safety and bounded work

The runtime limits hops, entities, evidence queries, candidates, context characters,
model output tokens, per-source/per-query time and total investigation time.
Initial collection shares the query budget. Failed queries are audited and not retried silently.
Source failures are isolated; zero candidates and insufficient evidence are normal abstention.

Preparation has a separate discovery deadline and estate entity/relationship/response limits.
An enabled topology source failure aborts preparation with a sanitized per-source report; a
partial graph is diagnostic only. In contrast, an evidence-query failure is audited in the
investigation and may lead to abstention. YAML references are bound strictly after discovery.

Query parameters remain local to the connector. Models receive catalog descriptions and IDs,
not arbitrary command authority. Local-only replay makes no network calls. Enabled YAML discovery
runs during `prepare`, `graph` and `investigate`, not just the separate discover command.
Kubernetes discovery is namespace/context scoped and excludes secret/environment payloads. HTTP support
is optional and refuses redirects, credential-bearing endpoints and oversized responses.

Redaction is heuristic, not a guarantee that arbitrary data is safe to export.
Keep credentials and personal data out of identifiers and operational payloads.
Operators remain responsible for approved telemetry access and model-provider data handling.

## Deliberately absent

No executor, auto-remediation, policy-controlled deployment, live telemetry receiver,
automatic incident ingestion, verified automatic rule learning, retrieval service
or production-readiness guarantee is implied.
These are incremental roadmap work, not placeholders that appear enabled in configuration.
Basic local Git log/diff inspection is available. Advanced orchestration, learning and governance
are not implemented yet; they are deferred until after PoC evaluation.

Loki/Tempo/Prefect read-only observation and scoped Tempo/Prefect topology adapters are
implemented; see [their query/configuration boundaries](telemetry-connectors.md). Typed
recent-change records (Git commits on mapped paths, Kubernetes rollouts) are evidence about
entities, not graph nodes; see [recent changes](telemetry-connectors.md#recent-changes) and
[why](design-notes/gridcast-integration-lessons.md#change-records).
