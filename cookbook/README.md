# Lumis SDK cookbooks

Cookbooks are small, runnable teaching projects that use Lumis SDK core in a specific domain. They are not part of the core package's runtime dependency set. Each cookbook owns its synthetic data, domain rules, knowledge documents, optional integrations, and setup instructions.

## Current cookbook domains

| Cookbook | Domain and lesson | Optional agent stack |
| --- | --- | --- |
| [simple-log-diagnosis](simple-log-diagnosis/README.md) | The smallest configuration-driven local diagnosis. | None |
| [recording-resolution](recording-resolution/README.md) | Save a human-confirmed outcome to local incident memory. | None |
| [data-pipeline-investigation](data-pipeline-investigation/README.md) | Schema drift, unfamiliar transformation failure, and telemetry redaction in a data pipeline. | Agno + OpenRouter |
| [ml-regression-monitoring](ml-regression-monitoring/README.md) | Feature drift, feature contracts, and candidate-model quality in one regression pipeline. | Agno + OpenRouter |
| [software-delivery-ci-investigation](software-delivery-ci-investigation/README.md) | CI lockfiles, workflow permissions, and Terraform references in one delivery pipeline. | Agno Toolkit + OpenRouter |
| [structured-rule-evaluation](structured-rule-evaluation/README.md) | Compound structured fields, required evidence, deterministic ranking, and JSON explanations. | None |
| [evidence-json-reporting](evidence-json-reporting/README.md) | Bounded local evidence collection, redaction, required evidence, and versioned JSON reports. | None |
| [plugin-package](plugin-package/README.md) | Independently packaged static manifest, lazy discovery, explicit loading, and contract testing. | None |
| [postgres-memory](postgres-memory/README.md) | Two processes share one explicit confirmed episode through the optional PostgreSQL plugin. | None |
| [webhook-http-evidence](webhook-http-evidence/README.md) | Authenticated replay-protected webhook normalization plus an offline HTTP JSON evidence plugin fixture. | None |
| [prometheus-alertmanager](prometheus-alertmanager/README.md) | Alertmanager normalization and synthetic Prometheus metric evidence mapped into a portable rule. | None |

## Offline smoke matrix

Every cookbook has a credential-free check. The check proves only the boundary named here; it is
not evidence that an external service or optional model works.

| Cookbook | Offline smoke path | What it validates |
| --- | --- | --- |
| simple-log-diagnosis | `uv run lumis diagnose --config cookbook/simple-log-diagnosis/lumis/lumis.yml` | Core CLI, rules, report, and SQLite memory. |
| recording-resolution | Run simple-log diagnosis, then use the printed ID with the documented `resolve` and `report` commands. | Explicit human truth transition; no inferred resolution. |
| data-pipeline-investigation | `uv run lumis doctor --config cookbook/data-pipeline-investigation/lumis/lumis.yml` | Owned config/rules/local paths; optional Agno/OpenRouter call is not exercised. |
| ml-regression-monitoring | `uv run lumis doctor --config cookbook/ml-regression-monitoring/lumis/lumis.yml` | Owned config/rules/local paths; optional model call is not exercised. |
| software-delivery-ci-investigation | `uv run lumis doctor --config cookbook/software-delivery-ci-investigation/lumis/lumis.yml` | Owned config/rules/local paths; optional model call is not exercised. |
| structured-rule-evaluation | `uv run lumis rules test --rule cookbook/structured-rule-evaluation/schema-change.yml --input cookbook/structured-rule-evaluation/schema-change.json` | Compound rule evaluation and explanation. |
| evidence-json-reporting | `uv run lumis diagnose --config cookbook/evidence-json-reporting/lumis/lumis.yml` | Bounded evidence, redaction, JSON report, and SQLite memory. |
| plugin-package | `uv run pytest cookbook/plugin-package/test_contract.py` | Static manifest and factory contract without provider authority. |
| postgres-memory | `uv run lumis doctor --config cookbook/postgres-memory/lumis.yml` | Secret reference and custom-schema config only; database behavior uses the Docker path. |
| webhook-http-evidence | CI command in its README using `httpx.MockTransport`. | Webhook and optional HTTP plugin composition without network. |
| prometheus-alertmanager | `uv run python cookbook/prometheus-alertmanager/demo.py` | Alert authentication, portable mapping, metric evidence, and deterministic rule. |
| guarded-proposal | `uv run python cookbook/guarded-proposal/demo.py` | Proposal and approval records remain non-executing. |
| verification-replay | `uv run python cookbook/verification-replay/demo.py` | Exact deterministic replay metrics. |

## Shared structure

Agentic cookbooks keep their framework-facing declaration in an `lumis/` directory:

```text
cookbook-name/
├── lumis/
│   ├── lumis.yml       # project, local state, report, and input paths
│   └── rules.yml          # project-owned deterministic rules
├── knowledge/             # optional runbooks and playbooks
├── synthetic_project/     # synthetic code and data only
└── README.md              # domain-specific teaching guide
```

This organization keeps configuration easy to find without mixing it with source, data, or provider-specific code. Relative paths in `lumis/lumis.yml` are resolved from that directory; the supplied cookbooks point local reports and SQLite memory back to their cookbook root.

## Adding a cookbook

Start with one bounded incident class and synthetic inputs. Explain the domain, the signals being tested, deterministic and unknown paths, safety boundary, and exact commands in the cookbook README. Keep optional providers and frameworks inside the cookbook. Add core functionality only when it is vendor-agnostic and useful to more than one cookbook.

The examples cover data pipelines, ML regression monitoring, software delivery, Prometheus-style
alerts, webhooks, shared memory, plugins, and governed recovery records. They are synthetic
teaching projects, not production integrations or external adopter endorsements.
