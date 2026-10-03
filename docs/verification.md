# SDK verification

Run from the repository. No consumer repository, paid model, cloud account or live testbed is
needed for these checks.

```bash
uv sync --locked --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/generate_config_schema.py --check
uv run pytest
uv run bandit --recursive --severity-level medium --confidence-level medium src
uv audit --locked
uv build
```

Repeat tests with supported Python versions using separate environments, for example
`UV_PROJECT_ENVIRONMENT=/tmp/lumis-tests-312 uv run --python 3.12 --all-groups pytest`.

The suite covers candidate contracts, sources sharing validation/evaluation, scoped graph,
deduplication, missing/conflicting/degraded/stale evidence, source/query timeouts, zero budget,
audited terminal states, record roundtrips, redaction, scoped topology, bounded HTTP serialization,
mocked Prometheus/OpenRouter/OpenAI/Anthropic/Gemini contracts and standalone CLI/YAML behavior.

Tests for the retired architecture are removed with their code, not counted as current coverage.

The suite also executes every code cell of the trusted offline notebook under an async event loop,
checks NetworkX parallel edges/cycles/export isolation, YAML discovery/binding, explicit aliases,
resource/service bridges, service-graph vector contracts, aggregate limits, source deadline,
cancellation, incomplete CLI reports and caller-owned HTTP client lifetime. Two independent
service/data-lineage inputs demonstrate the portable boundary; neither imports cookbook code.

## Independent distribution smoke

Build, install the wheel without the HTTP extra in an empty environment, then follow CLI
steps 2–5. CI repeats that workflow on Python 3.11/3.12/3.13 and asserts supported yet unconfirmed
output. Neither a GridCast checkout nor its cookbook is available to this smoke test.

Mock HTTP transport validates local contracts, not live provider availability or model quality.
Live consumer/provider qualification is a separate experiment with its own versioned evidence.
See [release gates](releasing.md); a passing SDK test suite is not a production-readiness claim.
