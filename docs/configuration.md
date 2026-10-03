# YAML configuration reference

The current project contract is `lumis.dev/operational-v1alpha1`.
Unknown fields, duplicate mapping keys, YAML aliases, excessive nesting and documents larger
than 1 MiB are rejected. Use explicit strings for identifiers and endpoints, native booleans
for checks and timezone-qualified timestamps in incident/evidence JSON.

## Incident-agent fields

The schema also includes checks and investigator. See the
[incident guide](incident-investigation.md#yaml-additions) for diagnostic signatures,
repository allowlists and budgets, and [sandbox settings](sandbox.md) for digest-pinned
experiments. Query provider probe requires an explicitly enabled sandbox and cannot be used
by deterministic signatures. Existing baseline fields below remain supported.

## Complete offline baseline example

```yaml
api_version: lumis.dev/operational-v1alpha1
project:
  name: my-estate
  environment: local

sources:
  kubernetes:
    enabled: false
  prometheus:
    enabled: false
  opentelemetry:
    enabled: false

policies:
  default_action_mode: read_only

graph:
  entities:
    - id: service:demo
      kind: service
      name: Demo service
      attributes:
        owner: reliability-team
        criticality: medium
  relationships: []

queries:
  - id: health
    provider: snapshot
    entity_id: service:demo
    key: healthy
    description: Was the service healthy during the incident?

initial_query_ids: []

rule_hypotheses:
  - id: service-unavailable
    statement: Service unavailability may explain the failure.
    causal_path: [service:demo]
    evidence_needed: [health]
    predictions:
      - {entity_id: "service:demo", key: healthy, operator: eq, value: false}
    falsifiers:
      - {entity_id: "service:demo", key: healthy, operator: eq, value: true}

budget:
  graph_hops: 3
  max_entities: 100
  max_queries: 8
  max_hypotheses: 5
  max_model_output_tokens: 3000
  max_context_characters: 20000
  query_timeout_seconds: 10
  source_timeout_seconds: 30
  total_timeout_seconds: 120
```

The generated scaffold is equivalent but uses JSON syntax, which is accepted by the YAML loader.
Validate any edited file with `lumis doctor --project FILE`.

## Fields

| Field | Meaning |
| --- | --- |
| `project.name` | Required non-secret project identity |
| `project.environment` | Local/dev/staging-style identity, default local |
| `sources` | Optional explicitly enabled connectors; all disabled by default |
| `identity.aliases` | Explicit raw ID → canonical ID mapping; no chains/cycles or guessed name joins |
| `discovery` | Separate estate discovery time/entity/edge/series/response bounds |
| `observations_file` | Optional normalized evidence JSON array, relative to YAML directory |
| `models` | Optional provider/model/key-variable configuration; OpenRouter default, also OpenAI/Anthropic/Gemini |
| `policies.default_action_mode` | Only `read_only` is supported; no action execution exists |
| `graph.entities` | Unique operational id/kind/name, string metadata attributes, provenance IDs |
| `graph.relationships` | Source/target/kind/provenance, endpoints must exist |
| `queries` | Unique operator-owned id/provider/entity/key/description/parameters |
| `initial_query_ids` | Registered queries collected before candidate generation, sharing the budget |
| `rule_hypotheses` | Falsifiable candidates with registered evidence IDs and graph references |
| `budget` | Limits on context size, topology scope, candidates, requests and time |

A causal path is a candidate's graph-referenced explanation, not verified causality.
Query/check references must exist; duplicate query or hypothesis IDs are rejected.
Supported checks are `eq`, `ne`, `gt`, `ge`, `lt`, `le`.
Ordered comparisons require numeric, non-boolean values.
Queries may reference declared **or discoverable** canonical entity IDs. When topology sources are
enabled, local validation defers graph membership to preparation; unresolved IDs still fail before
investigation. Doctor is not a completed discovery/binding check. Without discovery sources, local
validation immediately checks membership. Metadata enriches context, not action authority.

## Kubernetes discovery

```yaml
sources:
  kubernetes:
    enabled: true
    context: my-approved-context
    namespace: my-approved-namespace
```

Both scope fields are required. `kubectl` and read access to services, deployments, pods and
ReplicaSets are required. No kubeconfig edits, all-namespace scan, env/secret extraction or workload
mutation occurs. `discover`, `graph`, `investigate` and Python `prepare()` use the same discovery.
Approved `app.kubernetes.io/name` labels and namespace add logical `service:<namespace>:<name>`
entities; resource IDs stay distinct and connect to the logical entity through `hosts` edges.
Missing app labels do not cause guessed identities or service-call edges.

## OpenTelemetry export normalization

```yaml
sources:
  opentelemetry:
    enabled: true
    export_file: ./telemetry/traces.json
```

Relative paths resolve against the YAML directory. Input must be an OTLP JSON export with
`resourceSpans`; service namespace/name and same-trace parent references define topology.
This is a local export normalizer, not an OTLP ingestion endpoint or live trace query connector.
Payload attributes/baggage are not exported as graph context.

## Prometheus evidence

```yaml
sources:
  prometheus:
    enabled: true
    endpoint: http://localhost:9090
queries:
  - id: service-up
    provider: prometheus
    entity_id: service:demo
    key: up
    description: Availability at the end of the incident
    parameters:
      promql: 'min(up{job="demo"})'
```

Merge this query with your full valid project and update candidate check keys/values accordingly.
The adapter calls the instant-query API at the incident end time and requires one numeric scalar
or one vector series. Aggregate explicitly in operator-owned PromQL; the model cannot supply
PromQL. Multiple series, nonfinite values or invalid responses are not usable observations.
HTTP(S) endpoints may not include credentials, query parameters or fragments.
The current adapter does not expose a provider-authentication configuration; keep access scoped
through your operator-managed network boundary. HTTP is an optional extra.

## Prometheus service-graph discovery

```yaml
sources:
  prometheus:
    enabled: true
    endpoint: http://localhost:9090
    discover_service_graph: true
    service_namespace: my-estate
    service_graph_query: 'sum by (client, server) (rate(traces_service_graph_request_total[5m]))'
```

This consumes an existing service-graph metric (for example exported by a Tempo metrics-generator);
it does not query Tempo, install its generator or infer call topology from arbitrary `up` metrics.
The operator-owned expression must return a vector with nonempty `client` and `server` labels and
finite positive values. Zero values add no relationship; absence is not proof of no dependency.
Server → client `serves` edges use `service:<service_namespace>:<label>` IDs. An explicit namespace
is mandatory: the query must be scoped to one estate. Do not aggregate same-name services across
tenants/namespaces and relabel them as one estate. Warnings/partial results fail discovery.
`YamlProject.investigate()` queries at the incident end time. `prepare(at=...)` allows an explicit
time; standalone discovery/graph without a time uses the backend's current instant.

## External topology, aliases and discovery limits

```yaml
sources:
  topology:
    enabled: true
    file_path: ./estate.json
identity:
  aliases:
    'service:old-estate:frontend': 'service:canonical-frontend'
discovery:
  timeout_seconds: 30
  max_entities: 5000
  max_relationships: 10000
  max_service_graph_series: 1000
  max_response_bytes: 2000000
observations_file: ./observations.json
```

`estate.json` is a validated `GraphSnapshot`, not executable adapter code. Each local document is
also capped at 1 MiB. Aliases apply to discovered entity IDs and edge endpoints, not query/check
strings: queries, candidates, observations and incidents must use the canonical IDs already.
Do not collapse Kubernetes resources into services. Kind/metadata conflicts, alias chains and
cycles are rejected. A declared canonical target can supply the display name; many-to-one aliases
require compatible kinds/names/attributes. Conflicting namespace metadata is rejected, not erased.

The discovery budget covers preparation separately from the incident's `budget`. Aggregate
overflow is rejected, never silently truncated. A failed source leaves remaining sources
`not_checked`; the report is incomplete and investigation does not start. Local file reads are
synchronous but size bounded; the deadline primarily bounds asynchronous source waits. Cancellation
propagates. A prepared snapshot is reused only when you explicitly retain `PreparedProject`.

Live Kubernetes discovery reports **current** resources; requesting historical Prometheus time does
not reconstruct historical Kubernetes state. For reproducible replay, archive normalized topology
and observations externally and use file sources. There is no automatic snapshot history service.

## Optional model

```yaml
models:
  provider: openrouter
  model: your-explicit-provider/model-id
  api_key_env: OPENROUTER_API_KEY
```

No default model, auto-fallback or hidden call is used. Only `--use-model` or Python
`use_model=True` invokes this source.
Provider-specific key defaults and native configuration are in [model providers](models.md).
The environment variable name must use uppercase letters/digits/underscores and start with a letter.
Structured model output must contain 3–5 valid candidates. Availability, cost, privacy,
schema support and quality remain operator responsibilities.

## Incident and observations

`incident.json` contains `id`, `affected_entities`, `symptoms`, `started_at`, `ended_at`.
`observations.json` is an array of `Evidence` records: `id`, `query_id`, `entity_id`,
`key`, scalar `value`, `observed_at`, `source`, `retrieval_method`, optional `quality`
(`observed` or `degraded`). Values and check types must agree.
Observation time must fall within the incident window; source provenance is caller-owned.
If `observations_file` is configured, it is read automatically during investigation. An explicit
CLI `--observations` or Python `observations=` overrides it; `observations=()` forces missing evidence.

Checked editor schemas are in [schemas](../schemas). Regenerate with
`uv run python scripts/generate_config_schema.py`.
Design-pattern ideas such as Git, Prefect, Loki, Tempo, approval-required actions and automatic
rule promotion are not accepted as working configuration until their adapters/contracts ship.
