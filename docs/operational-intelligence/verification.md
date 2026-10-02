# Reset implementation verification

Local record: 2026-10-02, branch `feat/operational-intelligence-mvp`, based on `8a371d1` from
`origin/dev`. [PR #93](https://github.com/soloshun/lumis-sdk/pull/93) merged into `dev` at
`ad01fda7486224406b4df9cb0c3095953571f26b`; all ten PR checks passed, including both plugin
contracts/coexistence and the Python matrix. This record is not a release. Live gates remain
tracked in [#92](https://github.com/soloshun/lumis-sdk/issues/92).

## Passed locally

- 129 tests on Python 3.11.15, 3.12.13 and 3.13.13, including all pre-reset tests and 29 added
  operational/control regression tests. Existing legacy deprecation warnings remain expected.
- Ruff formatting/lint, strict mypy over 78 source files, generated schema checks, diff checks.
- Bandit at the CI medium-severity/medium-confidence threshold: no findings.
- `uv audit --locked`: no known vulnerabilities/adverse statuses in 33 audited packages.
- Wheel and source distribution built and passed existing release-content verification.
- Core-only wheel installed in a fresh environment without `httpx`; `lumis investigate` replay
  completed with the expected assessments, trace and unconfirmed truth.
- Optional HTTP adapters tested with real HTTP serialization and `httpx.MockTransport`: query
  shape/time, structured model output, no model tools, response-size/redirect constraints.
- Kubernetes List normalization and OTLP/JSON parent joins tested without a live cluster.
- Existing paper control-substrate evaluation rerun against this SDK over five repeats into a
  temporary output directory. All metric values and run digest matched its committed baseline.
  No research source/results were modified. This is compatibility evidence, not validation of
  the new model/hypothesis architecture's diagnostic quality.

## Still open

- No Kubernetes context is configured on this machine. Live GridCast discovery/observations
  and actual 3–5 model-candidate generation have not been verified.
- No paid OpenRouter call was made. Transport conformance is not model-quality evaluation.
- Independent fault corpus, baseline comparisons, cost/calibration/causal-path findings are OI-2/3.
- No executor exists. Recovery success, independent external security/adoption evidence and
  final `0.1.0` qualification are not established by these tests.

## Reproduce local checks

```bash
uv sync --frozen --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/generate_config_schema.py --check
uv run pytest
uv run bandit --recursive --severity-level medium --confidence-level medium \
  src packages/lumis-sdk-postgres-memory/src packages/lumis-sdk-http-json-evidence/src
uv audit --locked
uv build
uv run python scripts/verify_release_artifacts.py dist \
  --distribution lumis-sdk --version 0.1.0rc1
```

The version above identifies an **unpublished local build**, not replacement PyPI artifacts.
Pin the reviewed Git revision when handing it to GridCast. CI also runs the installed-wheel
replay on every supported Python version and existing independent plugin contracts.
