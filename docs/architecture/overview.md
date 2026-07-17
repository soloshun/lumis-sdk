# Lumis SDK architecture

Lumis SDK uses ports and adapters so that its incident and recovery semantics remain independent of a model provider, database, observability vendor, orchestration system, cloud or agent framework.

The [phased roadmap](../../ROADMAP.md) extends this architecture incrementally. Future model,
lineage, semantic-retrieval, and recovery protocols must preserve the dependency rule below and
remain either provider-neutral core contracts or independently installable adapters.

## Dependency rule

```text
entry points -> application -> domain
                       \-> ports <- adapters
```

- `domain` depends only on Python, Pydantic, and standard-library types.
- `application` coordinates use cases using domain models and ports.
- `ports` describe replaceable capabilities.
- `adapters` implement local or provider-specific behavior.
- `cli` selects and composes adapters.

## Current package map

| Package | Responsibility | Stability |
| --- | --- | --- |
| `lumis_sdk.domain` | Incidents, evidence, diagnoses, hypotheses, truth states, and guarded recovery state. | Canonical pre-1.0 API. |
| `lumis_sdk.application` | Deterministic-first diagnosis and recommendation-only lifecycle orchestration. | Canonical pre-1.0 API. |
| `lumis_sdk.ports` | Evidence, model, memory, reporting, context, policy, approval, verification, and audit boundaries. | Experimental; changes require compatibility notes. |
| `lumis_sdk.adapters.deterministic` | Explainable local rule matching. | Reference adapter. |
| `lumis_sdk.adapters.sqlite` | Local memory and transparent lexical retrieval. | Reference adapter. |
| `lumis_sdk.adapters.evidence` | Bounded local JSON evidence collection. | Reference adapter. |
| `lumis_sdk.adapters.reports` | Deterministic Markdown and versioned JSON reports. | Reference adapter. |
| `lumis_sdk.adapters.plugins` | Metadata-only discovery and explicit policy-checked loading. | Experimental plugin SDK. |
| `lumis_sdk.config` | Strict v1alpha1 documents, bounded loading, and schema. | Versioned configuration API. |
| `lumis_sdk.cli` | Local composition and user commands. | Pre-alpha public interface. |
| `lumis_sdk.testkit` | Deterministic fakes, fixtures, and reusable evidence/report contracts. | Experimental. |

## Evidence boundary

`EvidenceService` requests typed evidence through an async `EvidenceProvider`. It enforces
timeouts, kind filtering, stable duplicate handling, item and character budgets, and optional
redaction before evidence reaches diagnosis. Provider errors are returned as structured failures
so unavailable context cannot be mistaken for a confirmed observation.

The `local-json` adapter is an offline reference implementation. Independent packages can
implement the same port without introducing vendor types into domain or application code.

## Plugin boundary

Plugin distributions register the `lumis_sdk.plugins` entry-point group and ship a strict static
manifest. Discovery validates distribution identity, SDK compatibility, support status,
capabilities, and authority requests without importing plugin modules. Loading is explicit,
policy-checked, and isolated per plugin; core remains fully usable with no plugins installed.

## Deterministic diagnosis

Rules are evaluated by descending priority and then configured order. Each required rule ID is stable, and every match records its rule ID, version, priority, matched terms, and evidence IDs. The diagnosis remains a hypothesis and requires human review.

## Optional model routing

`DiagnosisService` invokes a `ModelGateway` only when deterministic classification is `unknown`, `ModelUsePolicy.enabled` is true, and a gateway is injected. The gateway receives bounded domain data and returns schema-validated diagnosis plus provider/model/prompt metadata. No provider SDK type appears in domain or application contracts.

## Memory truth

An incident without a human resolution is exposed as `unconfirmed_hypothesis`; adding a human resolution exposes `human_confirmed`. Later schema versions can persist rejected, superseded, and verification-confirmed states explicitly.

## Guarded lifecycle

The canonical application lifecycle retrieves context, diagnoses, proposes a plan, records
approval state, and records verification state. It has no action executor. Evidence collection,
persistence, and Markdown or JSON report writing are composed separately through their ports and
adapters.

## Contract maturity

Current public contracts remain pre-1.0 until Sprint 6 inventories stable, provisional, and
internal surfaces and publishes configuration v1 plus migration guarantees. Future breaking
changes require an explicit compatibility decision, versioned configuration or storage
transition, deprecation notice, upgrade guide, and contract fixtures. Stability never widens
runtime authority: plugin installation, approval, and model output remain non-authorizing by
default.
