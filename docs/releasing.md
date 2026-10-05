# Maintainer release runbook

The target remains experimental `0.1.0`, not `1.0.0`.
This file describes future publication; executing SDK cleanup does not itself publish.

## 1. Work and review on dev

Branch from current `origin/dev`, commit with DCO sign-off, open a PR to `dev`.
Run [verification](verification.md), review all removed paths and optional dependency boundaries,
then require CI, security and dependency checks to pass before merge.
Each sprint updates current docs, schemas, tests, roadmap and changelog together.

## 2. Choose a fresh candidate version

Before publishing this architecture, inspect existing PyPI/TestPyPI releases and tags.
Never reuse an existing artifact version. `0.1.0rc1` was uploaded for the previous
architecture; `0.1.0` (2026-10-05) is the first release of this one. For the next release,
update the version in `pyproject.toml`, `src/lumis_sdk/__init__.py`, the lockfile and the
changelog together.
Record intentional breaking migration and removed packages.

## 3. Verify SDK gates independently

Require supported Python tests; generated schemas; lint/type/security/dependency checks;
wheel and source-archive builds; archive-content checks; independent clean installations;
offline CLI init/doctor/discover/investigate; explicit API/CLI/YAML limitations.
Also require incident/menu/SVG and manual-resolution checks, optional-agent import isolation,
scripted native-provider construction, real Docker probe isolation/cleanup and the
[sandbox threat-model review](sandbox.md) appropriate to the claimed environment.
No live application completion is a prerequisite for this standalone framework milestone.

Qualify live optional providers separately before advertising their demonstrated behavior.
For a research artifact, pin the commit, Python, dependencies, input fixtures and measurements.
A live experiment not run stays unverified; do not present mock responses as live evidence.

## 4. Promote dev to main

Create/review a release PR from `dev` to `main`, preserving checked evidence.
Confirm the intended version, license, migration links and experimental public wording.
A merged dev PR does not promote main or publish anything.

## 5. Publish a candidate to TestPyPI

Open GitHub Actions → Release package → Run workflow → select `main`, exact declared version,
target `testpypi`. Environment approval and trusted publishing must be configured separately.
The workflow refuses non-main publication, reruns source checks, audits dependencies, compares
rebuild hashes, generates/attests SBOM and provenance, and clean-installs wheel/source archives.
Verify resulting artifacts and install from the index in a clean environment.

## 6. Publish to PyPI and record release evidence

Only an authorized release maintainer runs target `pypi`.
Use the qualified, unused candidate/final version. Verify uploaded metadata, installation,
CLI contract and source/tag correspondence. Create release notes and the matching Git tag
according to maintainer approval. Final `0.1.0` remains pre-1.0 and experimental.

## 7. Update issues and project board

Mark SDK implementation done only with merged code and verification.
Track actual consumer integration and future roadmap work separately. A legacy roadmap item
may be marked superseded with a historical branch pointer, not “implemented” by implication.
Do not silently close external review, live evaluation or operations gates.
