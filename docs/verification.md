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

The [telemetry connector suite](../tests/test_telemetry_connectors.py) additionally exercises
Loki/Tempo/Prefect wire serialization, incident windows, scoped read-only filters, redacted log/run/
span observations, malformed/empty/capped responses, optional topology and public runtime/agent
wiring. See [connector setup](telemetry-connectors.md); no live backend/consumer qualification is
implied by deterministic HTTP transports.

The [SQL connector suite](../tests/test_sql_connector.py) covers the query contract (single
read-only statement, window parameters only), transaction guards and value normalization with a
scripted driver. Its PostgreSQL test runs only with `LUMIS_TEST_POSTGRES_DSN` set (use a read-only
role); it also checks that a write is refused.

Tests for the retired architecture are removed with their code, not counted as current coverage.

The agent suite uses the real Pydantic AI loop with a scripted FunctionModel: dynamic tools,
structured output, budget exhaustion, repair of rejected output and malformed tool arguments,
per-candidate acceptance, malformed claims, triage escalation, source failure,
scoped code/Git, immutable candidate/probe bindings and separate manual resolution persistence.
Both notebooks execute offline. Scripted responses test protocol, not model quality.
Opt-in real Docker tests cover no network/credential forwarding, unprivileged execution,
read-only root, copied source, invalid/non-finite/oversized output and timeout/cancellation cleanup.
See [sandbox qualification](sandbox.md). CI runs these against a preloaded pinned image.

The suite also executes every code cell of the trusted offline notebook under an async event loop,
checks NetworkX parallel edges/cycles/export isolation, YAML discovery/binding, explicit aliases,
resource/service bridges, service-graph vector contracts, aggregate limits, source deadline,
cancellation, incomplete CLI reports and caller-owned HTTP client lifetime. Two independent
service/data-lineage inputs demonstrate the portable boundary; neither imports cookbook code.

## Independent distribution smoke

### Limited live transport smoke (2026-10-03)

Read-only requests against the already-running local GridCast backends verified real Loki log
queries, Tempo TraceQL search/OTLP span retrieval, and Prefect flow/task filters. The 24-hour
queries returned records; intentionally bounded results were correctly marked degraded at their
caps (20 log records, 100 trace matches and 20 flow records). A scoped task filter returned two
task records; an explicit trace returned a span observation. No fault was injected, workflow
state changed, remediation performed or paid model invoked. This is transport compatibility,
not representative incident diagnosis, telemetry completeness or consumer acceptance.

Real Prefect schemas revealed different flow/task sort enums; real Tempo search returned
unpadded hexadecimal IDs. Both compatibility cases now have regression coverage.

### Clean-wheel boundary

Build, install the wheel without the HTTP extra in an empty environment, then follow CLI
steps 2–5. CI repeats that workflow on Python 3.11/3.12/3.13 and asserts supported yet unconfirmed
output. Neither a GridCast checkout nor its cookbook is available to this smoke test.

Mock HTTP transport validates local contracts, not live provider availability or model quality.
Live consumer/provider qualification is a separate experiment with its own versioned evidence.
See [release gates](releasing.md); a passing SDK test suite is not a production-readiness claim.
