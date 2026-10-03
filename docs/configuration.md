# YAML configuration reference

The current project contract is `lumis.dev/operational-v1alpha1`.
Unknown fields, duplicate mapping keys, YAML aliases, excessive nesting and documents larger
than 1 MiB are rejected. Use explicit strings for identifiers and endpoints, native booleans
for checks and timezone-qualified timestamps in incident/evidence JSON.

## Complete offline example

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
Register queries on declared entities before investigating; merge discovered topology with declared
business entities explicitly. Metadata can enrich ownership/context, not authorize actions.

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
mutation occurs. Discovery is triggered only by `lumis discover`.

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

## Optional model

```yaml
models:
  provider: openrouter
  model: your-explicit-provider/model-id
  api_key_env: OPENROUTER_API_KEY
```

No default model, auto-fallback or hidden call is used. Only `--use-model` invokes this source.
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

Checked editor schemas are in [schemas](../schemas). Regenerate with
`uv run python scripts/generate_config_schema.py`.
Design-pattern ideas such as Git, Prefect, Loki, Tempo, approval-required actions and automatic
rule promotion are not accepted as working configuration until their adapters/contracts ship.
