# Contributing to Lumis SDK

Lumis is experimental, vendor-neutral operational-intelligence software.
Small, reviewable changes with tests and accurate documentation are welcome.

## Responsibility and provenance

Discuss substantial changes in an issue first. Use original code, public references and
synthetic/public data. Do not contribute private logs, customer information, credentials,
employer/client code or confidential architecture.

Every commit needs a Developer Certificate of Origin 1.1 sign-off (`git commit -s`):
you have the right to submit the work under Apache-2.0.

AI-assisted contributions are allowed. The human contributor must understand and explain the
work, verify correctness and security, respect licensing/provenance and privacy, follow the
architecture, and run the required checks. AI output is not proof that code is safe or correct.
Briefly disclose material AI assistance in the PR. Maintainers may request origins and reject
work that cannot be explained, verified or legally contributed.

## Current architecture

Read [architecture](docs/architecture.md) and [Python API](docs/python-api.md).
Core contracts are vendor-neutral. Sources propose the same falsifiable hypotheses.
The runtime owns evidence testing, scope and budgets. Models have no action authority.
Connect external applications through telemetry/ports; never import their ground truth.

There is one active architecture. Do not restore removed legacy namespaces, plugin discovery,
cookbooks or old schemas as compatibility shims. Historical reproduction belongs on a legacy
checkout. Application recipes belong in the separate Lumis cookbooks project.
Optional provider dependencies must not become core requirements.

## Setup and checks

```bash
uv sync --locked --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/generate_config_schema.py --check
uv run pytest
uv build
```

See [verification](docs/verification.md) for security, dependency and clean-install gates.

## PR workflow

1. Branch from current `dev`; target feature/fix PRs back to `dev`.
2. Explain portable adopter need, public API/configuration impact and safety/privacy boundaries.
3. Add tests, current documentation, schemas if needed and an unreleased changelog entry.
4. Sign off commits, disclose material AI use and require automated checks before merge.
5. Promote `dev` to `main` by a separate release PR; publishing is an explicitly authorized step.
   Follow [release runbook](docs/releasing.md).

Do not claim a live integration, measured model quality or production readiness from mocks.
Capabilities require a portable use case, authority/privacy/dependency assessment and offline
verification plan. Changes widening network/filesystem authority or adding execution need a
design discussion and threat-model update before implementation.
