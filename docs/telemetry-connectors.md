# Loki, Tempo and Prefect integration

These are optional **read-only query connectors**, usable from the same YAML, Python API,
CLI and investigator tools. They do not subscribe to incidents or ingest telemetry. Your
collector/application sends logs to Loki and traces to Tempo; Prefect owns workflow execution.
An explicit incident tells Lumis which graph entities and time window to investigate.

## 1. Install the reviewed development SDK

Use the current `dev` checkout with `uv sync --extra http --all-groups`, or install a built
wheel with `pip install 'lumis-sdk[http] @ file:///absolute/path/to/reviewed.whl'`.
Agent use additionally requires the `agent` extra and explicit model configuration.
The restructured architecture has not been published as a new index release.

## 2. Configure the real endpoints and identities

Start from the complete [telemetry project example](examples/telemetry-project.yaml).
Replace the declared entity, selectors and flow names with your real estate's identities.
Do not copy a service label that is absent from your telemetry.

```yaml
sources:
  loki:
    enabled: true
    endpoint: http://localhost:3100
    max_results: 50
  tempo:
    enabled: true
    endpoint: http://localhost:3200
    max_results: 50
  prefect:
    enabled: true
    endpoint: http://localhost:4200/api
    flow_names: [daily-forecast]
    max_results: 50
```

The Prefect endpoint is its **API base**, including `/api` on a default self-hosted server;
Lumis preserves path prefixes (including a Cloud account/workspace API base). Loki and Tempo
must point to their read/query frontend or monolithic endpoint, not an ingestion distributor.
Configured endpoints may not contain credentials, query strings or fragments.
Each source is disabled by default; an endpoint alone does not enable network access.

For authentication, use an environment reference, not an inline secret:

```yaml
sources:
  loki:
    enabled: true
    endpoint: https://approved-log-gateway.example
    headers_env:
      Authorization: LUMIS_LOKI_AUTHORIZATION
      X-Scope-OrgID: LUMIS_LOKI_TENANT
```

Set `LUMIS_LOKI_AUTHORIZATION` outside YAML to the complete authorization header value
(for example `Bearer <read-only-token>` or an approved Basic header). Tempo and Prefect accept
the same fields. Values are resolved at request time, sent only to the configured source,
and excluded from evidence/configuration. Missing values fail closed. Use narrowly scoped
credentials and HTTPS outside a trusted local lab. Do not give an injected shared HTTP client
global secret headers/cookies spanning different backends.

## 3. Register observation queries

Every query needs its own `id`, `entity_id`, `key`, description and provider. Models request IDs
through `inspect(operation="evidence", query_id=...)`; they cannot invent LogQL/TraceQL, change
endpoints, increase limits or select arbitrary Prefect flows. Parameters are strict:

| Provider | Parameters | Observation |
| --- | --- | --- |
| `loki` | `logql`, `output: entries` (default) | Timestamped, redacted log messages |
| `loki` | `logql`, `output: count` | Number of returned matching log records |
| `tempo` | `traceql`, `output: entries` (default) | Selected trace ID/root service/name/duration summaries |
| `tempo` | `traceql`, `output: duration_ms` | One numeric duration per returned trace |
| `tempo` | `trace_id`, `output: spans` | Bounded OTLP span identity, service, duration and status summaries |
| `tempo` | `traceql`, `output: spans` | Search then retrieve matching trace spans, without predeclared incident trace IDs |
| `prefect` | `flow_name`, `operation: flow_runs` (default), `output: entries` (default) | Selected run identity/state/time/duration summaries |
| `prefect` | Above, `operation: task_runs`, `flow_run_id` | Task observations for an explicit approved flow run |
| `prefect` | Either operation, `output: failed_count` or `max_duration_ms` | Failed/crashed count or maximum total runtime of the returned runs |

Loki requires at least one nonempty exact label matcher and stream-returning LogQL.
Tempo search requires an exact resource matcher; operators must also scope the environment.
These checks are not complete query-language parsers; backend syntax validation still applies.
Prefect requires an explicit source flow-name allowlist; each query must belong to it.

Log counts are not failure rates; Tempo searches are sampled matches, not population percentiles.
Multiple duration samples stay distinct observations, rather than silently becoming an average.
Prefect queries select runs **started within** the incident. They use current-state APIs and
require the returned state transition to be within the incident window. They cannot reconstruct
historical states or all long-running jobs that began before the incident. `total_run_time` is
Prefect's accumulated runtime, converted from seconds to milliseconds, not exclusively elapsed
time inside the incident. Raw parameters/results/state messages and arbitrary span attributes,
baggage or Loki structured metadata are not exported. Approved log messages are untrusted data.
Redaction is conservative, not a guarantee that arbitrary telemetry contains no sensitive data.

## 4. Optionally discover observed topology

Tempo can search an explicit time-bounded TraceQL scope, fetch at most ten traces, and join
cross-service parent spans. Alternatively supply up to ten explicit `discover_trace_ids`.

```yaml
sources:
  tempo:
    enabled: true
    endpoint: http://localhost:3200
    discovery_query: '{ resource.service.namespace = "demo-estate" }'
    service_namespace: demo-estate
    lookback_seconds: 3600
    max_spans: 1000
  prefect:
    enabled: true
    endpoint: http://localhost:4200/api
    flow_names: [daily-forecast]
    discover_topology: true
    namespace: demo-estate
    lookback_seconds: 3600
```

Tempo identities are `service:<service.namespace>:<service.name>`. Spans without a matching
namespace are excluded. Flow identities are `workflow:<namespace>:<flow-name>`; observed runs
are `prefect:flow-run:<UUID>` and `prefect:task-run:<UUID>`. Task-input references create
upstream-task → dependent-task `feeds` edges only when both tasks were observed. Containment
is `task → flow-run → workflow`. No missing flow/node or causal link is fabricated from a name.
Use explicit `identity.aliases` to map discovered IDs onto declared canonical entities.

Discovery is an observed snapshot, not a guarantee of complete lineage or historical replay.
Missing/uninstrumented parent spans have no inferred edge. Empty successful discovery can have
zero entities; unresolved query references still fail preparation. Capped workflow/task lists,
trace searches exceeding ten, invalid responses, HTTP errors or discovery deadlines block
preparation and produce sanitized source statuses. Aggregate graph bounds remain enforced.

## 5. Inspect, then investigate

```bash
lumis doctor --project ./lumis.yaml
lumis discover --project ./lumis.yaml --report
lumis graph --project ./lumis.yaml --format svg --output ./estate.svg
lumis incident --project ./lumis.yaml --incident ./incident.json --store ./incidents.sqlite
```

Use real timezone-aware incident start/end timestamps and declared/discovered affected IDs.
For a notebook, use top-level `await`:

```python
from pathlib import Path
from lumis_sdk.core import Incident
from lumis_sdk.runtime import YamlProject
from lumis_sdk.runtime.documents import read_document

project = YamlProject.from_file("./lumis.yaml")
incident = Incident.model_validate_json(read_document(Path("./incident.json")))
report = await project.handle_incident(incident)  # no paid model call
print(report.context.evidence)
print([(receipt.status, receipt.purpose) for receipt in report.receipts])
```

Add queries to `initial_query_ids` or a diagnostic rule to retrieve them without a model.
Otherwise an explicitly enabled investigator can request them dynamically. Add `use_agent=True`
only after approving its model/settings. A connector alone does not supply diagnostic rules.

## Bounds, uncertainty and verification

Each source has `max_results` (1–100, default 50), `max_response_bytes` (default 1 MB) and
`max_requests` (default 32 per connector instance). The runtime creates fresh connectors per
investigation. Discovery and per-query/total investigation deadlines are separately enforced.
Tempo search-to-spans retrieval also has `max_trace_reads` (1–10, default five); all fetched spans
share the result/byte/request/deadline bounds. Search caps degrade the resulting span facts.
No redirects, implicit pagination or hidden retries are used. Prefect's POST filter calls are
read-only; no create, retry, state-change or deployment endpoint is reachable through these tools.
Exhaustion/errors/malformed or out-of-window observations are unavailable, not false evidence.
Empty results produce no facts, never an invented zero. Results at a cap are `degraded` and
cannot certify a deterministic diagnosis; narrow the query/window. An incomplete discovery
cannot be used as a prepared graph. Raw backend errors are not report content.

Run `uv run pytest tests/test_telemetry_connectors.py` for independent HTTP serialization,
scope/auth/redaction, time/byte/item/request/graph bounds, topology and public API/agent checks.
These deterministic transports do not claim a live GridCast run or real provider accuracy.
See [verification](verification.md) and [consumer qualification](integrations.md).

OpenTelemetry's `4317` is an OTLP ingestion port, not a log/trace retrieval API. Keep your
collector sending telemetry to the backends; configure `sources.tempo.endpoint` for querying
and `sources.opentelemetry.export_file` for offline exports. No live SDK receiver is implemented.
OpenLineage ingestion and typed recent-change queries remain unimplemented.

## Read-only SQL (PostgreSQL)

Install the `sql` extra (`lumis-sdk[sql]`, psycopg 3). The connection string is read from the
environment variable named by `dsn_env`, never from configuration:

```yaml
sources:
  sql:
    enabled: true
    dsn_env: ESTATE_READONLY_DSN      # e.g. postgresql://reader@db:5432/estate
    statement_timeout_ms: 5000
    connect_timeout_seconds: 5
queries:
  - id: model-alias-moves
    provider: sql
    entity_id: service:estate:forecast-service
    key: production_alias_changes_30m
    description: Production alias moves in the 30 minutes before incident end
    parameters:
      sql: >-
        SELECT count(*) FROM ml.model_events WHERE event = 'alias_set'
        AND at > %(ended_at)s - interval '30 minutes' AND at <= %(ended_at)s
```

Each query is one `SELECT`/`WITH` statement returning exactly one row with one column (number,
boolean or text; text is redacted). `%(started_at)s` and `%(ended_at)s` bind the incident window;
no other parameters are accepted and a literal `%` is written `%%`. Every query runs in its own
read-only transaction (`default_transaction_read_only`, `SET TRANSACTION READ ONLY`) with the
statement timeout and is rolled back. The transaction mode is a guard, not a permission boundary:
connect as a role that can only `SELECT` the tables you register. `NULL` yields no observation;
the observation time is the incident end. Errors are reported only as unavailable evidence.

API references: [Loki query API](https://grafana.com/docs/loki/latest/reference/loki-http-api/),
[Tempo query API](https://grafana.com/docs/tempo/latest/api_docs/),
[Prefect flow filters](https://docs.prefect.io/v3/api-ref/rest-api/server/flow-runs/read-flow-runs)
and [task filters](https://docs.prefect.io/v3/api-ref/rest-api/server/task-runs/read-task-runs).
