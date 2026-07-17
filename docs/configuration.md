# Lumis SDK configuration reference

Lumis SDK configuration is a versioned public API. `lumis.dev/v1` documents are strict: unknown fields fail validation, paths resolve from the project document, and model use is disabled unless explicitly enabled and composed with a gateway. Released `v1alpha1` documents remain readable through `1.x`; see the [migration guide](migrations/config-v1.md).

## Project document

```yaml
apiVersion: lumis.dev/v1
kind: Project
metadata:
  name: customer-pipeline
  labels:
    domain: data
spec:
  environment: local
  memory:
    provider: sqlite
    path: .lumis/incidents.db
  reports:
    provider: markdown
    outputDir: .lumis/reports
  incidentSources:
    - provider: local-log
      path: logs/latest-failure.log
  evidenceProviders:
    - provider: local-json
      path: evidence/schema-diff.json
      kinds: [schema-diff]
      maxItems: 20
      maxTotalCharacters: 50000
      maxItemCharacters: 10000
      timeoutSeconds: 5
      redact: true
  rules:
    files: [rules.yml]
  model:
    enabled: false
```

| Field | Required | Meaning |
| --- | --- | --- |
| `apiVersion` | Yes | Must be `lumis.dev/v1`. Versioning prevents silent behavior changes. |
| `kind` | Yes | Must be `Project`. |
| `metadata.name` | Yes | Stable project/pipeline identifier used in incidents and reports. |
| `metadata.labels` | No | Project-owned string labels for future adapters and policy. |
| `spec.environment` | No | Environment label; defaults to `local`. |
| `spec.memory.provider` | No | `sqlite` by default; `postgres` selects the optional plugin configuration. |
| `spec.memory.path` | No | Local SQLite path, relative to project YAML. SQLite only. |
| `spec.reports.provider` | No | `markdown` or `json` in the reference package. |
| `spec.reports.outputDir` | No | Report directory, relative to project YAML. |
| `spec.incidentSources` | No | Bounded source declarations. v1 includes `local-log`. |
| `spec.evidenceProviders` | No | Ordered bounded evidence declarations. v1 includes `local-json`. |
| `spec.rules.files` | No | Ordered versioned `DiagnosisRuleSet` documents. |
| `spec.model.enabled` | No | Explicit policy flag; defaults to `false`. It does not install or select a provider. |

### Evidence provider fields

| Field | Meaning |
| --- | --- |
| `provider` | Reference provider name. v1 supports `local-json`. |
| `path` | Local JSON file containing an item list or `{"items": [...]}`. |
| `kinds` | Optional evidence-kind allowlist. Empty means all supplied kinds. |
| `maxItems` | Maximum accepted items after filtering and duplicate removal. |
| `maxTotalCharacters` | Maximum combined detail size accepted from the provider. |
| `maxItemCharacters` | Maximum detail size for one item. Longer details are marked and truncated. |
| `timeoutSeconds` | Collection deadline enforced by the application service. |
| `redact` | Conservatively redact likely secrets before evidence enters diagnosis or reports. |

Provider errors, malformed files, timeouts, and unreadable paths become structured collection
failures. They do not silently become facts and do not grant network, execution, or broader
filesystem authority.

### HTTP JSON evidence fields

The optional `lumis-sdk-http-json-evidence` package uses the following strict configuration:

| Field | Meaning |
| --- | --- |
| `url` | Exact HTTPS endpoint. Embedded credentials and fragments are rejected. |
| `allowedOrigins` | Required unique HTTPS origin allowlist; the configured URL origin must match. |
| `tokenEnv` | Optional environment-variable name containing an authentication token. |
| `authHeader` | Authentication header name; defaults to `Authorization`. |
| `authScheme` | Authentication scheme; defaults to `Bearer`. |
| `maxResponseBytes` | Streamed response-byte cap before JSON parsing. |
| `timeoutSeconds` | HTTP client deadline, also enforced by `EvidenceService`. |
| `retries` | Immediate bounded retries for timeouts, network failures, 429, and 5xx; 0 to 3. |

The connector always disables redirects and sends minimized incident identity/environment fields,
requested kinds, and bounds. It does not send `IncidentInput.raw_payload`. The reference CLI
validates this configuration but does not load the optional plugin; applications compose it
through the Python/plugin API.

### PostgreSQL memory fields

```yaml
spec:
  memory:
    provider: postgres
    connectionUrlEnv: LUMIS_MEMORY_DATABASE_URL
    schema: lumis_memory
    connectTimeoutSeconds: 10
    maxSearchCandidates: 1000
```

| Field | Meaning |
| --- | --- |
| `connectionUrlEnv` | Required environment-variable name containing the connection URL. Never the URL itself. |
| `schema` | Validated lowercase schema owned by the adapter. Defaults to `lumis_memory`. |
| `connectTimeoutSeconds` | Per-operation connection timeout from 1 to 60 seconds. |
| `maxSearchCandidates` | Maximum rows considered before public ranking; 1 to 10,000. |

PostgreSQL requires the independently packaged `lumis-sdk-postgres-memory` plugin. Discovery does
not grant its declared network or secret authorities. The reference report-aware CLI store remains
SQLite-only; applications compose the asynchronous PostgreSQL `MemoryStore` through the Python
and plugin API. See [RFC 0002](rfcs/0002-postgresql-memory.md).

## Rule-set document

```yaml
apiVersion: lumis.dev/v1
kind: DiagnosisRuleSet
metadata:
  name: customer-pipeline-rules
spec:
  rules:
    - id: missing-customer-id
      name: missing-customer-id
      version: "1"
      priority: 100
      all_contains: ["KeyError", "customer_id"]
      classification: schema_change
      severity: medium
      summary: A required customer identifier was unavailable.
      root_cause_hypothesis: The upstream schema or normalization mapping may have changed.
      confidence: 0.65
      missing_evidence:
        - current input schema
        - previous successful schema
      recommended_next_steps:
        - Compare the current and previous successful schemas.
        - Review recent upstream and normalization changes.
      suggested_playbook: investigate_schema_contract
```

### Rule fields

| Field | Meaning |
| --- | --- |
| `id` | Required stable machine-readable identity used in explanations and evidence references. |
| `name` | Human-readable rule name retained in reports. |
| `version` | Project-controlled rule revision. Change it when the rule meaning changes. |
| `priority` | Higher values run first. Equal priorities retain configured order. |
| `all_contains` | Every text fragment must occur case-insensitively in the supplied log. |
| `classification` | Project-defined failure category. |
| `severity` | `low`, `medium`, `high`, or `critical`. |
| `summary` | Short description of the observed failure class. |
| `root_cause_hypothesis` | Possible cause, explicitly not a confirmed fact. |
| `confidence` | Human-authored calibration of the hypothesis given this signature. |
| `missing_evidence` | Context needed to strengthen, contradict, or reject the hypothesis. |
| `recommended_next_steps` | Safe investigation work; not automatically executed. |
| `suggested_playbook` | Candidate playbook name; never execution authority. |

## Confidence

Lumis SDK does not calculate deterministic-rule confidence. The rule author sets it to communicate how strongly the matched signature supports the configured **hypothesis**.

A specific error plus a verified schema diff may justify higher confidence than a generic timeout string. Start conservatively, include missing evidence, review confirmed outcomes, and revise the rule version when calibration changes.

Confidence must not authorize remediation. Risk, approval, execution, and verification are separate contracts. A model-provided confidence is also an unconfirmed claim until supported and reviewed.

## Match ordering and explanation

Rules run by descending priority and then file/configuration order. A successful match exposes rule ID, version, priority, matched terms, and evidence IDs through `diagnose_text_with_explanation`. Equal-priority rules retain their declared order.

For structured incident fields, use one strict `kind: DiagnosisRule` document per file. Structured
rules support `all`, `any`, `not`, string and numeric comparisons, required evidence, priority,
specificity, stable input-order tie breaking, and explanations for every candidate. See the
[structured-rules API guide](python-api/structured-rules.md).

## Path behavior

Relative paths resolve and normalize from the project YAML location. In a cookbook where YAML lives under `lumis/`, local state can live at cookbook root:

```yaml
spec:
  memory:
    path: ../.lumis/incidents.db
  reports:
    outputDir: ../.lumis/reports
```

Configured paths are local authority granted by the user running Lumis SDK. Plugin and hosted adapters require separate path/network/permission policies.

## Validation and doctor

```bash
uv run lumis doctor --config path/to/lumis.yml
uv run lumis rules validate --config path/to/lumis.yml
uv run lumis rules validate --config path/to/lumis.yml --json
uv run lumis rules test --rule path/to/rule.yml --input path/to/fixture.json
```

`doctor` validates project/rule documents, reports selected local providers, checks the local-log path when configured, and warns when model policy is enabled. It does not write incident state or contact a network service.

The checked [project schema](../schemas/lumis-project-v1.schema.json),
[legacy rule-set schema](../schemas/lumis-rules-v1.schema.json), and
[structured diagnosis-rule schema](../schemas/lumis-diagnosis-rule-v1.schema.json) can be
used by editors. JSON report consumers can validate against the
[diagnosis-report schema](../schemas/lumis-diagnosis-report-v1.schema.json). CI verifies
that all checked schemas match the Pydantic contracts.

## Upgrade from v1alpha1

```bash
lumis config migrate path/to/lumis.yml --output path/to/lumis.v1.yml
```

Migrate the project and all referenced rule files together. Mixed-version collections are
rejected. The migration is validated, idempotent, and refuses to overwrite an existing output
unless `--force` is explicit. See the complete [v1 migration guide](migrations/config-v1.md).

## Secrets

Do not put plaintext credentials in project YAML. PostgreSQL memory accepts only
`connectionUrlEnv`, an environment-variable reference. Other provider adapters should define typed
secret references and document the environment or secret-manager boundary. Model providers cannot
be selected by adding an undocumented field to core configuration.

## Current limits

- Project and rule files are limited to one MiB each.
- The reference CLI reads local logs up to ten MiB.
- The local JSON evidence adapter reads files up to one MiB; collection applies configured item,
  per-item character, total-character, timeout, kind, duplicate-ID, and redaction limits.
- The optional HTTP JSON connector additionally requires HTTPS, an exact origin allowlist,
  redirect rejection, minimized outbound metadata, bounded retries, and a response-byte cap.
- Legacy rule sets remain limited to deterministic `all_contains`.
- Structured `DiagnosisRule` documents support `all`, `any`, `not`, regex, structured fields,
  numeric thresholds, required evidence, and deterministic ranking.
- Time windows, schema-aware type coercion, conflict analytics, and compiled indexes remain
  roadmap work.
