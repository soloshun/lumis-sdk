# Changelog

All notable changes to Lumis SDK are recorded here. The project follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses [Semantic Versioning](https://semver.org/) once release versions are established.

## Unreleased

### Added

- Added stable `lumis.dev/v1` schemas for project, rule-set, structured-rule, diagnosis-report,
  plugin-manifest, playbook, and recovery-policy documents while retaining frozen alpha schemas.
- Added validated, deterministic, idempotent migration APIs and `lumis config migrate` with
  non-overwriting output by default.
- Added a public API stability inventory, compatibility/deprecation policy, and v1 upgrade guide.
- Added release artifact content validation, deterministic rebuild comparison, SPDX SBOMs, signed
  provenance/SBOM attestations, Python 3.11–3.13 clean wheel/sdist installs, plugin coexistence,
  PR dependency/license review, secret scanning, and a security/authority review record.
- Added a navigable documentation index, core concepts, standalone core/plugin adoption evidence,
  a Prometheus/Alertmanager walkthrough, expanded custom PostgreSQL-schema guidance, offline smoke
  paths for every cookbook, and a versioned Phase 1 tutorial/video script.
- Added explicit core/plugin governance, contributor provenance and support boundaries, a
  reproducible Phase 1 benchmark harness, and a step-by-step `0.1.0rc1` to `0.1.0` release guide.
- Explicitly allow responsible AI-assisted contributions while retaining human accountability,
  provenance, architecture, safety, documentation, and verification requirements.

### Changed

- New projects, reports, plugin manifests, policies, playbooks, and repository cookbooks now use
  `lumis.dev/v1`; project/rule alpha loading remains available through `1.x`.
- YAML configuration now rejects aliases and nesting deeper than 64 nodes before model validation.

### Deprecated

- `lumis.dev/v1alpha1` project and rule documents now emit
  `LumisV1Alpha1DeprecationWarning` and are planned for removal in `2.0`.

## [0.0.8] - 2026-07-16

### Added

- Added strict versioned playbook, deterministic policy, evidence-linked proposal, and
  approval-decision contracts with bounded typed parameters, expiry, immutable revision
  references, canonical JSON, and SHA-256 digests.
- Added a proposal-only application service and idempotent reference approval ledger; core still
  exposes no action executor or execution authority.
- Added explicit verification requests, checks, records, conservative truth transitions,
  verification-aware learning, rejection/supersession persistence, reusable-only retrieval, and
  transparent lexical/filter/truth score components.
- Added deterministic replay cases and exact-match metrics, checked policy/playbook/proposal
  schemas, RFC 0003, API documentation, and offline proposal/replay cookbooks.

### Fixed

- Plugin discovery now reads each distribution's own uniquely packaged static manifest, allowing
  multiple independently installed plugins to coexist without overwriting one shared
  `lumis-plugin.json` path.

### Security

- High-risk proposals cannot auto-approve, unknown actions and missing policy rules fail closed,
  proposal parameters are allowlisted and bounded, and approval does not grant execution.
- Failed, unknown, and timed-out verification cannot report success or become reusable memory.

## [0.0.7] - 2026-07-16

### Added

- Accepted RFC 0002 for provider-neutral shared-memory configuration, idempotency, migrations,
  bounded retrieval, and explicit plugin authority.
- Added reusable asynchronous `MemoryStore` contract assertions and an async SQLite reference
  adapter while preserving the existing report-aware CLI store.
- Added strict secret-referenced PostgreSQL memory configuration and checked schema.
- Added the independently installable `lumis-sdk-postgres-memory` plugin with serialized
  migrations, fixed SQL, explicit network/secrets authority, contract tests, and Docker cookbook.
- Added framework-neutral HMAC webhook normalization with strict payload structure, timestamp
  skew, delivery IDs, injectable replay protection, and hostile-input tests.
- Added strict allowlisted HTTP JSON evidence configuration and the independently installable
  `lumis-sdk-http-json-evidence` plugin with minimized requests, redirect rejection, bounded
  retries/responses, structured failures, offline transport tests, and a fixture cookbook.

### Security

- Memory idempotency conflicts and resolutions for absent incidents fail closed.
- PostgreSQL credentials remain outside YAML, schema identifiers are validated and quoted, and
  candidate retrieval is bounded.
- Webhook secrets and connector tokens remain environment references; forged, stale, replayed,
  duplicate-key, deeply nested, oversized, redirected, and non-allowlisted inputs fail closed.

## [0.0.6] - 2026-07-16

### Added

- RFC-governed `lumis_sdk.plugins` discovery with strict static manifests and checked schema.
- Metadata-only plugin listing and doctor commands that do not import plugin modules.
- SDK compatibility, support status, capability, duplicate, archived, and authority checks.
- Explicit policy-checked plugin loading with isolated import/factory failures.
- Reusable plugin manifest/factory fixtures and contract assertions for independent packages.
- Plugin API, compatibility, migration, packaging, and security documentation.

## [0.0.5] - 2026-07-16

### Added

- Explicit bounded `anyElement` and `allElements` comparisons for list-valued structured fields.
- Quantified condition explanations with matched element indexes and bounded observed values.
- A stable testkit fixture for list-valued incident fields.

### Security

- Empty, nested, non-list, and lists above 100 elements fail quantified comparisons closed.

## [0.0.4] - 2026-07-16

### Added

- Structured diagnoses can declare `spec.diagnosis.missingEvidence` for follow-up evidence needs
  without weakening `spec.evidence.required` match preconditions.

### Changed

- Rule validation rejects values duplicated between required and post-match outstanding evidence.
- `lumis rules test` now exposes the selected diagnosis classification and outstanding evidence.

## [0.0.3] - 2026-07-16

### Added

- A vendor-neutral async evidence-provider port and bounded collection service with deadlines,
  kind filtering, duplicate handling, redaction, truncation, and structured failures.
- A local JSON evidence adapter and strict project configuration for evidence budgets.
- Versioned JSON diagnosis reports, checked JSON Schema, round-trip parsing, and CLI composition.
- Stable testkit fixtures, fake evidence providers, and reusable evidence/report contract checks.
- API documentation and a synthetic evidence-to-JSON-report cookbook.

### Changed

- Expanded `doctor` to verify configured local evidence paths.
- Added tracked delivery-sprint sequencing to the public roadmap.
- Updated release artifact actions and hardened the published-package verifier for cached indexes
  and TestPyPI dependency resolution.

## [0.0.2] - 2026-07-16

### Added

- Strict single-file `DiagnosisRule` documents with compound `all`/`any`/`not` evaluation,
  structured and numeric conditions, required evidence, deterministic specificity ranking,
  candidate explanations, JSON Schema, CLI fixture testing, and an `all_contains` migration path.
- Open-source repository automation for `main`/`dev` CI, supported-Python testing, locked
  dependency audits, Bandit SAST, Dependabot updates into `dev`, issue/PR templates, CODEOWNERS,
  and a maintainer runbook.

### Changed

- Added Python 3.12 and 3.13 to the tested compatibility matrix.
- Upgraded the development test dependency to a release that fixes CVE-2025-71176.

## [0.0.1] - 2026-07-15

### Added

- A ports-and-adapters package layout with vendor-neutral domain models, application services, explicit extension ports, reference adapters, and deterministic test fakes.
- Strict `lumis.dev/v1alpha1` `Project` and `DiagnosisRuleSet` documents, checked JSON Schema, bounded file loading, stable rule IDs, versions, priorities, and match explanations.
- `lumis init`, `lumis doctor`, and `lumis rules validate` commands.
- Architecture audit, phased refactor plan, threat model, governance, support, and roadmap documentation.
- `ml-regression-monitoring`, a synthetic housing-regression cookbook covering deterministic feature drift, unfamiliar feature-contract failures, and candidate-model quality regression.
- `software-delivery-ci-investigation`, a synthetic CI cookbook covering deterministic lockfile mismatch, workflow-permission, and infrastructure-reference incidents.
- A cookbook-local `lumis/` configuration layout and teaching material that explains the human-authored meaning of rule confidence.
- Configuration-driven deterministic diagnosis, Markdown reports, local SQLite incident memory, and transparent keyword search.
- An optional provider-neutral model gateway boundary with structured-output validation and conservative redaction.
- Non-executing lifecycle contracts for context, policy, approval, verification, and audit adapters.
- Synthetic data-pipeline, ML-regression, software-delivery, and resolution cookbooks.
- This changelog.

### Changed

- Established the Lumis SDK public identity: `lumis-sdk` on package indexes, `lumis_sdk` in Python, and `lumis` on the command line.
- Reframed Lumis SDK as a deterministic-first framework for guarded incident recovery: Diagnosis-as-Code is the implemented foundation and guarded Healing-as-Code is the roadmap direction.
- Replaced the flat proof-of-concept modules with canonical domain, application, port, adapter, configuration, security, CLI, and testkit packages.
- Updated every repository cookbook to use the canonical package structure and strict versioned configuration.
- Versioned every bundled cookbook configuration without moving cookbook-specific scenarios into core.
- Replaced the previous SVG mark with a plain text wordmark until a durable visual identity is designed.
- Renamed the provider-named agent demonstration to `data-pipeline-investigation` so the cookbook name describes its domain rather than its optional implementation choices.
- Moved cookbook `lumis.yml` and `rules.yml` files into cookbook-local `lumis/` directories.
- Replaced scripted demo-agent tool sequences with domain-specific incident-response system policies; Agno now exposes tool definitions from function names, signatures, and docstrings for the model to select as needed.

### Security

- Live model calls remain opt-in and excluded from CI; all repository examples are synthetic.
