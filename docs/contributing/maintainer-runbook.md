# Lumis SDK maintainer runbook

This runbook defines the repository flow for maintainers and contributors. Lumis SDK remains
an independently useful open-source framework; Lumis consumes released SDK versions and does
not receive private SDK-only behavior.

## Branch model

- `main` is the latest reviewed release line.
- `dev` is the integration branch for the next release.
- Feature, fix, documentation, security, and release branches start from the latest `dev`.
- Pull requests normally target `dev`.
- A release pull request promotes reviewed `dev` changes into `main`.
- Emergency release fixes start from `main`, merge into `main`, and are immediately reconciled
  back into `dev`.

```bash
git switch dev
git pull --ff-only origin dev
git switch -c feat/sdk-123-short-description
```

Before opening a pull request:

```bash
uv sync --frozen --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/generate_config_schema.py --check
uv run pytest
uv build
```

## Issue intake

1. Confirm the request is generally useful without the Lumis hosted product.
2. Map it to `ROADMAP.md` and label the affected contract.
3. Record the adopter impact, acceptance criteria, compatibility path, and verification plan.
4. Require an RFC for a new port, breaking model/config change, plugin-system change, execution
   capability, default model behavior, remote telemetry, or governance change.
5. Keep product-specific UI, tenancy, billing, hosted connectors, and enterprise policy outside
   the SDK repository.

An issue is complete only when implementation, tests, public documentation, schema or example
updates, and changelog notes are present as applicable. Close it from the merged pull request so
the implementation remains traceable.

## Pull-request review

Review in this order:

1. Architecture boundaries and vendor independence.
2. Safety, privacy, evidence, and authority changes.
3. Public-contract compatibility and migration.
4. Tests, schemas, deterministic behavior, and failure modes.
5. Documentation accuracy and implemented-versus-roadmap claims.

Required checks are CI, dependency audit, and static security analysis. Branch protection should
require these checks, one approving review, resolved conversations, and disallow force pushes to
`main` and `dev`.

## Dependency updates

Dependabot opens weekly GitHub Actions and `uv` pull requests against `dev`. Review lockfile
changes, release notes, licensing, and security impact. Do not merge a dependency update merely
because tests pass; confirm that it does not widen runtime authority or introduce a mandatory
provider dependency.

## Release

1. Confirm `dev` is green and the changelog describes all adopter-visible changes.
2. Open a release pull request from `dev` to `main`.
3. Review version, compatibility notes, generated schemas, and clean-install behavior.
4. Merge to `main`.
5. Manually dispatch the release workflow with the package selection and exact
   `pyproject.toml` version.
6. Publish to TestPyPI first when packaging or metadata changed, then publish to PyPI.
7. Create the GitHub release and verify the installed package with
   `scripts/verify_published_package.sh`.
8. Update Lumis only after the public SDK release is available.

PyPI publication remains a maintainer-controlled manual action through Trusted Publishing.
The same workflow publishes `core`, `postgres-memory`, and `http-json-evidence` independently;
each distribution retains its own semantic version and must pass its package-specific contracts.
