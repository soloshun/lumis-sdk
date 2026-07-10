# Changelog

All notable changes to OpenARIA are recorded here. The project follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses [Semantic Versioning](https://semver.org/) once release versions are established.

## [Unreleased]

### Added

- `ml-regression-monitoring`, a synthetic housing-regression cookbook covering deterministic feature drift, unfamiliar feature-contract failures, and candidate-model quality regression.
- `software-delivery-ci-investigation`, a synthetic CI cookbook covering deterministic lockfile mismatch, workflow-permission, and infrastructure-reference incidents.
- A cookbook-local `openaria/` configuration layout and teaching material that explains the human-authored meaning of rule confidence.
- This changelog.

### Changed

- Renamed the provider-named agent demonstration to `data-pipeline-investigation` so the cookbook name describes its domain rather than its optional implementation choices.
- Moved cookbook `openaria.yml` and `rules.yml` files into cookbook-local `openaria/` directories.
- Replaced scripted demo-agent tool sequences with domain-specific incident-response system policies; Agno now exposes tool definitions from function names, signatures, and docstrings for the model to select as needed.

## [0.1.0] - 2026-07-10

### Added

- Configuration-driven deterministic diagnosis, Markdown reports, local SQLite incident memory, and transparent keyword search.
- Optional provider-neutral model gateway boundary with structured-output validation and conservative redaction.
- Non-executing lifecycle contracts for context, policy, approval, verification, and audit adapters.
- Synthetic data-pipeline and resolution cookbooks.

### Security

- Live model calls remain opt-in and excluded from CI; all repository examples are synthetic.
