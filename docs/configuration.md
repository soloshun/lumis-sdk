# OpenARIA configuration reference

OpenARIA configuration is a versioned public API. `openaria.dev/v1alpha1` documents are strict: unknown fields fail validation, paths resolve from the project document, and model use is disabled unless explicitly enabled and composed with a gateway.

## Project document

```yaml
apiVersion: openaria.dev/v1alpha1
kind: Project
metadata:
  name: customer-pipeline
  labels:
    domain: data
spec:
  environment: local
  memory:
    provider: sqlite
    path: .openaria/incidents.db
  reports:
    provider: markdown
    outputDir: .openaria/reports
  incidentSources:
    - provider: local-log
      path: logs/latest-failure.log
  rules:
    files: [rules.yml]
  model:
    enabled: false
```

| Field | Required | Meaning |
| --- | --- | --- |
| `apiVersion` | Yes | Must be `openaria.dev/v1alpha1`. Versioning prevents silent behavior changes. |
| `kind` | Yes | Must be `Project`. |
| `metadata.name` | Yes | Stable project/pipeline identifier used in incidents and reports. |
| `metadata.labels` | No | Project-owned string labels for future adapters and policy. |
| `spec.environment` | No | Environment label; defaults to `local`. |
| `spec.memory.provider` | No | `sqlite` in the reference package. Other providers implement a port. |
| `spec.memory.path` | No | Local SQLite path, relative to project YAML. |
| `spec.reports.provider` | No | `markdown` in the reference package. |
| `spec.reports.outputDir` | No | Report directory, relative to project YAML. |
| `spec.incidentSources` | No | Bounded source declarations. v1alpha1 includes `local-log`. |
| `spec.rules.files` | No | Ordered versioned `DiagnosisRuleSet` documents. |
| `spec.model.enabled` | No | Explicit policy flag; defaults to `false`. It does not install or select a provider. |

## Rule-set document

```yaml
apiVersion: openaria.dev/v1alpha1
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

OpenARIA does not calculate deterministic-rule confidence. The rule author sets it to communicate how strongly the matched signature supports the configured **hypothesis**.

A specific error plus a verified schema diff may justify higher confidence than a generic timeout string. Start conservatively, include missing evidence, review confirmed outcomes, and revise the rule version when calibration changes.

Confidence must not authorize remediation. Risk, approval, execution, and verification are separate contracts. A model-provided confidence is also an unconfirmed claim until supported and reviewed.

## Match ordering and explanation

Rules run by descending priority and then file/configuration order. A successful match exposes rule ID, version, priority, matched terms, and evidence IDs through `diagnose_text_with_explanation`. Equal-priority rules retain their declared order.

## Path behavior

Relative paths resolve and normalize from the project YAML location. In a cookbook where YAML lives under `openaria/`, local state can live at cookbook root:

```yaml
spec:
  memory:
    path: ../.openaria/incidents.db
  reports:
    outputDir: ../.openaria/reports
```

Configured paths are local authority granted by the user running OpenARIA. Plugin and hosted adapters require separate path/network/permission policies.

## Validation and doctor

```bash
uv run openaria doctor --config path/to/openaria.yml
uv run openaria rules validate --config path/to/openaria.yml
uv run openaria rules validate --config path/to/openaria.yml --json
```

`doctor` validates project/rule documents, reports selected local providers, checks the local-log path when configured, and warns when model policy is enabled. It does not write incident state or contact a network service.

The checked [project schema](../schemas/openaria-project-v1alpha1.schema.json) and [rule-set schema](../schemas/openaria-rules-v1alpha1.schema.json) can be used by editors. CI verifies that both match the Pydantic contracts.

## Secrets

Do not put plaintext credentials in project YAML. v1alpha1 intentionally has no generic secret string. Provider adapters should define typed secret references and document the environment or secret-manager boundary. Model providers cannot be selected by adding an undocumented field to core configuration.

## Current limits

- Project and rule files are limited to one MiB each.
- The reference CLI reads local logs up to ten MiB.
- Rule matching currently supports deterministic `all_contains`.
- `all`, `any`, `not`, regex, structured fields, thresholds, and conflict analytics remain roadmap work backed by future tests and version notes.
