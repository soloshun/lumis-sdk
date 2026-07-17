# Contributing to Lumis SDK

Thanks for contributing. Lumis SDK is a pre-alpha, safety-focused open-source framework and research companion. Small, reviewable, well-tested changes are preferred.

## Before you contribute

- Discuss substantial changes in an issue before investing in a pull request.
- Use only original code, public documentation, and synthetic or public data.
- Never submit credentials, private logs, customer information, employer/client code, runbooks, or architecture material.
- Keep the current release focused on diagnosis, recommendations, and guarded-recovery contracts; production remediation is out of scope.

## Architecture boundaries

- Put vendor-neutral models and invariants in `lumis_sdk.domain`.
- Put orchestration in `lumis_sdk.application` and abstract dependencies behind `lumis_sdk.ports`.
- Put SQLite, Markdown, deterministic engines, and future provider implementations in `lumis_sdk.adapters`.
- Keep provider SDKs, synthetic scenarios, prompts, runbooks, and project rules out of the domain.
- Prefer separate packages for substantial vendor adapters. Optional dependencies must not become core requirements.
- Treat configuration, serialized records, CLI output, and public Python imports as versioned contracts. Document future transitions rather than silently breaking them.

## Documentation and public claims

- Treat [`docs/LUMIS_SDK_REFERENCE.md`](docs/LUMIS_SDK_REFERENCE.md) as the canonical narrative for the framework.
- Keep the README accurate, task-oriented, and consistent with the core reference when public behavior changes.
- Distinguish implemented functionality from lifecycle contracts, cookbook demonstrations, and roadmap ideas. Do not describe a future connector, autonomous action, or hosted product as present functionality.
- Keep project-specific logs, rules, runbooks, and playbooks in a cookbook or consuming project; do not move scenario-specific material into `src/lumis_sdk`.
- “Diagnosis-as-Code” names the current structured, evidence-grounded capability. “Healing-as-Code” is the longer-term guarded-recovery direction; do not describe it as implemented until its policy, approval, execution, and verification mechanisms exist and are tested.

## Local setup

```bash
uv sync --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/generate_config_schema.py --check
uv run pytest
uv build
```

## Pull requests

- Branch from `dev` and open feature/fix pull requests back into `dev`. `main` is promoted from
  `dev` through a release pull request. See the
  [maintainer runbook](docs/contributing/maintainer-runbook.md).
- Keep the pull request focused and explain the user-visible behavior.
- Add or update tests for code changes.
- Update documentation and examples when behavior changes.
- Add an entry under `CHANGELOG.md` when behavior, configuration, safety posture, or a public interface changes.
- Do not add secrets to commits, fixtures, screenshots, or issue text.

Changes that add action execution, widen filesystem/network authority, alter approval semantics, or weaken evidence boundaries require a design discussion and explicit threat-model updates before implementation.

We welcome contributions to code, examples, cookbook recipes, and documentation. Changes to homepage messaging, branding, roadmap, sponsorship links, or product positioning are controlled by maintainers and may require prior discussion.

## Roadmap contribution intake

The [phased roadmap](ROADMAP.md) keeps future phases documentation-only until maintainers approve
one sprint. Before proposing a roadmap capability:

1. show a standalone or second-product use case rather than a Lumis-only requirement;
2. classify the work as core, official optional package, community package, example, or
   product-only;
3. identify authority, privacy, compatibility, dependency, maintenance, and migration impact;
4. provide synthetic/public fixtures and an offline verification plan; and
5. explain which existing port or contract is reused before proposing a new one.

Contributions may include written tutorials and reproducible video scripts. Every video must have
a versioned written equivalent so users can learn and verify the example without relying on an
external platform.
