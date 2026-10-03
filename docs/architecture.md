# Standalone operational intelligence

## Responsibility

Lumis is an independent framework for testing explanations about operational incidents.
A consuming application provides telemetry and integration adapters; it is not imported into
the kernel. A specific testbed's release, deployment or cookbook cannot block SDK implementation.

The working rule is “LLM proposes; Lumis tests.” Evidence support is not formal proof,
a confirmed root cause, or permission to execute a change.

## Current flow

Incident + declared/discovered topology → bounded context → rules / retrieved candidates /
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
| `graph` | Directed indexed adjacency and bounded neighborhood traversal |
| `connectors` | Read-only external topology and observation adapters |
| `reasoning` | Interchangeable candidate sources and mechanical assessment |
| `models` | Optional model adapter, no decision or action authority |
| `runtime` | Investigation loop, project parsing, scaffold and SQLite records |
| `security` | Conservative model/report context redaction |
| `cli` | Explicit composition of the public contracts |

Indexed standard-library adjacency keeps the core dependency footprint small. Traversal is
cycle-safe and refuses entity-budget overflow. No graph database is required for this milestone.
Relationship directions represent observed/declared operational relations, not proven causality.

## Safety and bounded work

The runtime limits hops, entities, evidence queries, candidates, context characters,
model output tokens, per-source/per-query time and total investigation time.
Initial collection shares the query budget. Failed queries are audited and not retried silently.
Source failures are isolated; zero candidates and insufficient evidence are normal abstention.

Query parameters remain local to the connector. Models receive catalog descriptions and IDs,
not arbitrary command authority. Local replay makes no network calls. Kubernetes discovery
is explicit, namespace/context scoped and excludes secret/environment payloads. HTTP support
is optional and refuses redirects, credential-bearing endpoints and oversized responses.

Redaction is heuristic, not a guarantee that arbitrary data is safe to export.
Keep credentials and personal data out of identifiers and operational payloads.
Operators remain responsible for approved telemetry access and model-provider data handling.

## Deliberately absent

No executor, auto-remediation, policy-controlled deployment, live telemetry receiver,
automatic incident ingestion, verified automatic rule learning, retrieval service,
Git/Prefect/Loki/Tempo connector or production-readiness guarantee is implied.
These are incremental roadmap work, not placeholders that appear enabled in configuration.
