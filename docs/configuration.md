# OpenARIA project configuration

OpenARIA is a framework. A project tells it what to diagnose through an `openaria.yml` file. The framework reads that configuration, evaluates its rules against an incident, writes a structured report, and saves local incident memory.

The configuration belongs to the consuming project or cookbook, not to OpenARIA itself.

## Complete example

```yaml
project: stock_feature_pipeline
environment: local

memory:
  path: .openaria/incidents.db

reports:
  output_dir: .openaria/reports

telemetry:
  log: logs/latest-failure.log

rules_file: rules.yml
```

The external `rules.yml` file contains the rule definitions:

```yaml
rules:
  - name: missing-close-column
    all_contains:
      - "KeyError"
      - "Close"
    classification: schema_change
    severity: medium
    summary: A transformation expected the Close field, but the supplied log shows it was unavailable.
    root_cause_hypothesis: The source schema may have changed, or a project normalization step may have renamed or removed Close.
    confidence: 0.65
    missing_evidence:
      - current input schema
      - last successful input schema
      - recent code changes
    recommended_next_steps:
      - Compare the current input schema with the last successful run.
      - Confirm whether the upstream source changed its exported fields.
    suggested_playbook: schema_mismatch_in_dataframe
```

## Top-level fields

| Field | Required | Meaning |
| --- | --- | --- |
| `project` | Yes | A project identifier shown as the pipeline name in reports. |
| `environment` | No | Deployment context; defaults to `local`. |
| `memory.path` | No | SQLite file for incident history; defaults to `.openaria/incidents.db`. Relative paths are resolved from the YAML file. |
| `reports.output_dir` | No | Directory for generated Markdown reports; defaults to `.openaria/reports`. Relative paths are resolved from the YAML file. |
| `telemetry.log` | No | Default local log path for `openaria diagnose`. Use `--log` to override it for one command. |
| `rules_file` | No | Relative or absolute YAML/JSON file containing ordered deterministic rules. |
| `rules` | No | Inline deterministic rules. Use this only for a small configuration; rules from `rules_file` are appended after inline rules. |

## Rule fields

Rules are evaluated in order. OpenARIA uses the **first** rule whose `all_contains` terms all appear in the supplied log, case-insensitively.

| Field | Required | Meaning |
| --- | --- | --- |
| `name` | Yes | Human-readable rule identifier included in the report. |
| `all_contains` | Yes | One or more text fragments that must all be present in the log. |
| `classification` | Yes | Project-defined failure category, such as `schema_change` or `upstream_source_change`. |
| `severity` | Yes | `low`, `medium`, `high`, or `critical`. |
| `summary` | Yes | Short description of what the rule means. |
| `root_cause_hypothesis` | Yes | A possible cause. It is always rendered as a hypothesis, not a confirmed fact. |
| `confidence` | Yes | Number from `0` to `1`; for example, `0.65` renders as 65%. |
| `missing_evidence` | No | Evidence that would make the diagnosis more reliable. |
| `recommended_next_steps` | No | Safe investigation steps for a human. |
| `suggested_playbook` | No | Name of a project playbook to recommend. OpenARIA does not execute it. |

## What `all_contains` means

For this rule:

```yaml
all_contains:
  - "KeyError"
  - "Close"
```

OpenARIA matches a log only when it contains both terms. The terms may occur on the same line or different lines, and matching ignores case. A log containing only `KeyError` does not match this rule. This keeps the first deterministic version simple and reviewable.

When several rules could match, order them from the most specific to the most general because the first match wins.

## Run a configured project

```bash
uv run openaria diagnose --config path/to/openaria.yml
```

When `telemetry.log` is not configured, pass the input explicitly:

```bash
uv run openaria diagnose --config path/to/openaria.yml --log path/to/failure.log
```

OpenARIA writes a Markdown report and stores the incident in the configured SQLite file. The command prints an incident ID.

```bash
uv run openaria report <incident-id> --config path/to/openaria.yml
uv run openaria resolve <incident-id> \
  --resolution "Describe the human-confirmed outcome." \
  --config path/to/openaria.yml
uv run openaria memory search "search terms" --config path/to/openaria.yml
```

`resolve` records a human-confirmed outcome. It does not infer, apply, or verify a production fix.

## Current boundary

The current configuration supports local deterministic diagnosis, reports, and local incident memory. Future cookbook adapters may use the same framework models and lifecycle interfaces to retrieve logs from APIs, query lineage, use an optional model gateway, request approval, or verify an action. Those integrations remain outside the base framework configuration until their contracts are implemented and documented.
