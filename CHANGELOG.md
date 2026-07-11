# Changelog

All notable changes to OpenARIA are recorded here. The project follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses [Semantic Versioning](https://semver.org/) once release versions are established.

## [Unreleased]

### Added

- A ports-and-adapters package layout with vendor-neutral domain models, application services, explicit extension ports, reference adapters, and deterministic test fakes.
- Strict `openaria.dev/v1alpha1` `Project` and `DiagnosisRuleSet` documents, checked JSON Schema, bounded file loading, stable rule IDs, versions, priorities, and match explanations.
- `openaria init`, `openaria doctor`, and `openaria rules validate` commands.
- Architecture audit, phased refactor plan, threat model, governance, support, and roadmap documentation.
- `ml-regression-monitoring`, a synthetic housing-regression cookbook covering deterministic feature drift, unfamiliar feature-contract failures, and candidate-model quality regression.
- `software-delivery-ci-investigation`, a synthetic CI cookbook covering deterministic lockfile mismatch, workflow-permission, and infrastructure-reference incidents.
- A cookbook-local `openaria/` configuration layout and teaching material that explains the human-authored meaning of rule confidence.
- This changelog.

### Changed

- Reframed OpenARIA as a deterministic-first framework for guarded incident recovery: Diagnosis-as-Code is the implemented foundation and guarded Healing-as-Code is the roadmap direction.
- Replaced the flat proof-of-concept modules with canonical domain, application, port, adapter, configuration, security, CLI, and testkit packages.
- Updated every repository cookbook to use the canonical package structure and strict versioned configuration.
- Versioned every bundled cookbook configuration without moving cookbook-specific scenarios into core.
- Replaced the previous SVG mark with a plain text wordmark until a durable visual identity is designed.
- Renamed the provider-named agent demonstration to `data-pipeline-investigation` so the cookbook name describes its domain rather than its optional implementation choices.
- Moved cookbook `openaria.yml` and `rules.yml` files into cookbook-local `openaria/` directories.
- Replaced scripted demo-agent tool sequences with domain-specific incident-response system policies; Agno now exposes tool definitions from function names, signatures, and docstrings for the model to select as needed.

## [0.0.1] - 2026-07-11

### Added

- Configuration-driven deterministic diagnosis, Markdown reports, local SQLite incident memory, and transparent keyword search.
- Optional provider-neutral model gateway boundary with structured-output validation and conservative redaction.
- Non-executing lifecycle contracts for context, policy, approval, verification, and audit adapters.
- Synthetic data-pipeline and resolution cookbooks.

### Security

- Live model calls remain opt-in and excluded from CI; all repository examples are synthetic.
