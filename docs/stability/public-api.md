# Public API stability inventory

This inventory defines what Lumis SDK intends to keep compatible across the `1.x` release line.
It separates portable framework contracts from reference implementations and implementation
details. A public import is not automatically stable unless it appears here or in the generated
API reference.

## Stability levels

| Level | Meaning |
| --- | --- |
| Stable | Changes follow semantic versioning. Backward-incompatible changes wait for a major release. |
| Provisional | Publicly usable and documented, but feedback may require a breaking change before it is promoted. |
| Internal | No compatibility promise. Importing it couples an adopter to implementation details. |

## Stable surface for 1.x

| Surface | Stable contract |
| --- | --- |
| Core domain | Public models exported by `lumis_sdk.domain` for incidents, evidence, diagnosis, truth state, reports, plugins, proposals, approvals, and verification. |
| Application services | Public services and functions exported by `lumis_sdk.application`, including deterministic-first diagnosis, bounded evidence collection, proposal validation, verification learning, and guarded lifecycle coordination. |
| Ports | Protocols exported by `lumis_sdk.ports`. New optional protocol methods require a new protocol or a major release. |
| Configuration | `lumis.dev/v1` `Project`, `DiagnosisRuleSet`, and `DiagnosisRule` documents and their checked schemas. |
| Serialized documents | `lumis.dev/v1` `DiagnosisReport`, `PluginManifest`, `Playbook`, and `RecoveryPolicy` envelopes and checked schemas. |
| Plugin discovery | Static manifest semantics, entry-point group, compatibility interval, support status, capability declarations, and default-deny authority checks. |
| Persistence port | The asynchronous `MemoryStore` behavior and reusable contract suite. Database tables, indexes, and migration implementation details are not public contracts. |
| CLI | Command names, exit-code classes, and documented machine-readable JSON output for `rules validate`, `rules test`, `plugins list`, and `plugins doctor`. Human-oriented prose may improve without a major release. |
| Testkit | Documented fixtures and contract assertions exported by `lumis_sdk.testkit`. Fixture contents may gain optional fields while preserving existing assertions. |

The stable serialized schemas are checked in under `schemas/*-v1.schema.json`. Additive optional
fields may appear in a minor release. Required fields, field meaning, enum removal, and default
behavior do not change incompatibly within `1.x`.

## Provisional surface

- Recovery execution is intentionally absent. Future executor and verifier protocols require an
  accepted RFC and remain provisional until separately promoted.
- `ActionProposal` is a stable Python model for Phase 1 workflows, but its standalone
  `lumis-action-proposal-v1alpha1.schema.json` lacks a versioned document envelope and remains
  provisional as a cross-language wire format.
- Concrete adapters in `lumis_sdk.adapters` are reference implementations. Their documented
  constructor behavior is supported, while private helpers and storage layout are internal.
- Optional PostgreSQL and HTTP connector packages follow their own versions and compatibility
  ranges. Their core port behavior is stable; provider-specific tuning remains adapter-owned.
- Replay metric breadth, lexical ranking weights, and benchmark numbers are provisional. Truth
  semantics and deterministic score component visibility are stable.

## Internal surface

- Names beginning with `_`, modules not exported from a package `__init__`, generated caches,
  SQLite/PostgreSQL table layouts, SQL statements, CLI composition helpers, and test-only package
  internals.
- Repository automation, cookbook fixture details, and private maintainer/project-board metadata.
- Loomis product tenancy, billing, hosted secrets, UI, and deployment concerns. They are consumers
  of the SDK, not SDK contracts.

## Change process

Stable changes require tests, documentation, changelog entries, and compatibility review.
Breaking proposals require an RFC, migration path, deprecation period where practical, and a
major release. See the [compatibility policy](compatibility.md) and
[v1 migration guide](../migrations/config-v1.md).
