# PoC maintenance verification — 11 October 2026

This is the review handoff for [SDK-M01–SDK-M17](poc-review-notes.md), on
`fix/poc-maintenance`, based on `dev` at `d6a40fc`. Portable implementation and offline
qualification are complete; maintainer approval and the listed live checks remain separate.
No release has been published and package metadata remains `0.1.0`.

## Start reviewing here

1. Read the per-item implementation records and checklists in the
   [maintenance backlog](poc-review-notes.md). Original suggestions are retained as historical
   review context; the dated entries state what subsequently changed.
2. Read [incident investigation](../incident-investigation.md) for failure reasons, receipt
   visibility, named tools, provisional states and candidate-round boundaries.
3. Read [model setup](../models.md) for Pydantic AI Bedrock Converse, optional dependencies,
   AWS credential-chain behavior, Anthropic cache controls and live qualification steps.
4. Read [Python API](../python-api.md), [CLI](../cli.md) and [glossary](../glossary.md).
   Existing `investigate()` has a different baseline contract; the new incident alias is
   `investigate_incident()`. Existing enums, `handle_incident()` and JSON CLI output are retained.
5. Run the [SDK playground](../notebooks/sdk-playground.ipynb) using its
   [setup instructions](../notebooks/README.md). It now writes and prints a cited Markdown report.
   Compare the four readable snapshots in `tests/fixtures/reports` with the notebook scenarios.

## Verified locally

On Python 3.11.15, Pydantic AI 2.54.0:

- Full suite: **247 passed, 8 skipped**. Seven skips are explicitly enabled Docker qualification
  cases; the other is the optional live PostgreSQL connector test.
- Docker-enabled agent/safety suite: **45 passed**, using the already-cached approved image
  `python@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016`.
- Ruff formatting/lint, strict source mypy, generated-schema freshness and Git whitespace checks.
- Bandit medium/high checks: no issues. Locked dependency audit: no known vulnerabilities or
  adverse project statuses in the 75 audited packages.
- Wheel and source archive build, plus an empty-environment core-only wheel smoke: version,
  project scaffold, doctor, incident Markdown and imports all work without Pydantic AI or boto3.

Reproduce the normal gates:

```bash
uv sync --locked --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/generate_config_schema.py --check
uv run pytest -q
uv run bandit --recursive --severity-level medium --confidence-level medium src
uv audit --locked
uv build
```

With the approved Docker image preloaded, reproduce isolation qualification:

```bash
LUMIS_TEST_SANDBOX_IMAGE=python@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016 \
  uv run pytest tests/test_investigation_safety.py tests/test_incident_agent.py -q
```

Tests in `tests/test_poc_maintenance.py` use synthetic observations, a real scripted Pydantic AI
loop, mocked Anthropic HTTP and a botocore-stubbed Bedrock Converse call. They verify cache
controls/accounting and the Converse wire contract, not paid-service availability or quality.
`tests/test_documented_notebook.py` checks all four full Markdown snapshots while executing
the trusted offline playground. Rendering does not call a model or apply patches.

## Review findings addressed

- Follow-up proposals require attempts for **every** requested query in the initial round,
  including failed reads and synthetic probe attempts. Partial acquisition does not open the
  next round; failure still means unknown, never false.
- Provisional evidence and cached-receipt links are independently validated in reports.
- Candidate-state summaries share the tool-content budget; omitted states are explicitly marked.
- Cached failure receipts retain the original failure status and provenance with no hidden retry.
- Markdown escapes untrusted links/HTML and identifies caller-reported symptoms, tentative
  suggestions, missing checks and unconfirmed support.
- Numeric overlap warnings are advisory and bounded; deterministic evaluation is unchanged.
- A synthetic healthy/no-fault control rules out the outage signature without producing a
  supported diagnosis; the external GridCast control still needs separate qualification.

## Still requiring separate qualification

- SDK-M10/M11: repeat the external GridCast comparison for tool errors, requests, tokens and
  diagnosis outcomes. Scripted runs are protocol evidence, not measured model improvement.
- SDK-M12: measure real cache reads/writes, model-specific minimums, TTL and billed costs.
- SDK-M15: repeat the GridCast recency scenario and a no-fault control; instruction changes do
  not establish timing or causality mechanically.
- SDK-M16: operator-approved live Bedrock account/region/IAM/model qualification using
  [the live procedure](../models.md#aws-bedrock-investigator).
- Hosted CI across supported Python versions and maintainer approval before merge/release.

No private Core engine code, enterprise workflows or consumer ground truth was imported. Public
Pydantic AI providers are preferred; additional provider names are recorded for incremental
adoption, not silently made selectable. MCP, DBOS and arbitrary endpoint tools remain separate
design proposals. The AWS skills informed explicit token limits, transport retry/timeouts,
credential-chain use and client cleanup; these are offline implementation checks, not AWS
deployment or production qualification.
