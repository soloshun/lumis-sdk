# OpenARIA

**Vendor-agnostic, guarded self-healing for data, ML, and software delivery pipelines.**

OpenARIA is an open-source, clean-room framework for turning failed data, machine learning, and software delivery pipelines into structured incident reports, evidence-grounded diagnoses, safe recommended next steps, and reusable operational memory.

OpenARIA v0.1 focuses on **Diagnosis-as-Code**. It does not perform automatic production remediation.

## What Diagnosis-as-Code means

Diagnosis-as-Code is OpenARIA's name for making incident diagnosis reproducible, inspectable, and structured instead of leaving it as scattered log reading or tribal knowledge. A failure is converted into a normalized incident, observed evidence, an explicitly uncertain root-cause hypothesis, missing context, and safe next steps.

The output is deliberately reviewable: it distinguishes facts from hypotheses and records the evidence behind each claim. Diagnosis-as-Code is not automatic remediation. In v0.1, OpenARIA recommends what an engineer should investigate; it does not execute production actions.

## Status

OpenARIA is an early proof of concept. It is designed for projects to declare their incident-diagnosis behavior in `openaria.yml` and use the framework from their own code, CLI workflows, or cookbooks.

## Development

OpenARIA uses [uv](https://docs.astral.sh/uv/) to manage Python and dependencies. Python 3.11 or newer is required.

```bash
uv sync --all-groups
uv run openaria --help
uv run pytest
```

## Configure a project

An OpenARIA project declares its own memory location, report location, and deterministic rules in `openaria.yml`. The framework evaluates those rules; it does not contain your pipeline-specific error signatures or playbooks.

```yaml
project: my_pipeline
memory:
  path: .openaria/incidents.db
telemetry:
  log: logs/latest-failure.log
rules_file: rules.yml
```

## Run a cookbook

The simple-log cookbook supplies synthetic input and a project configuration:

```bash
uv run openaria diagnose \
  --config cookbook/simple-log-diagnosis/openaria.yml \
  --log cookbook/simple-log-diagnosis/failure.log
```

The command writes the report and local SQLite memory where that cookbook's YAML configuration specifies. It uses no external network service, LLM, or remediation action.

## Local incident memory

Each diagnosis is saved in local SQLite memory at `.openaria/incidents.db`. The command prints an incident ID that can be used to retrieve the report, save a final resolution, or find matching past incidents:

```bash
uv run openaria report <incident-id> --config openaria.yml
uv run openaria resolve <incident-id> --resolution "Describe the confirmed resolution." --config openaria.yml
uv run openaria memory search "search terms" --config openaria.yml
```

Search is local, transparent keyword matching. It does not send incident data anywhere.

## Optional model assistance

The core includes a provider-neutral model boundary that is disabled by default. If a future integration is enabled, OpenARIA minimizes and redacts the log context before it reaches the gateway, validates the structured response against the same diagnosis schema, and falls back to deterministic diagnosis when no model gateway is configured or the response is invalid.

The core does not require an LLM provider or agent framework. Provider-specific examples, including the planned Agno + OpenRouter cookbook, remain opt-in and separate from the core package.

## Framework and cookbooks

OpenARIA is built as a lightweight framework with typed incident, diagnosis, memory, model-gateway, policy, approval, and verification interfaces. Cookbooks are separate, runnable projects that depend on those public interfaces rather than embedding framework logic themselves.

See [Framework and cookbook architecture](docs/framework-and-cookbooks.md) for the boundary between the reusable core and the synthetic agent demo, and [project configuration](docs/configuration.md) for the `openaria.yml` schema.

## Safety and clean-room policy

Use only public knowledge, original code, public documentation, and synthetic examples. Do not contribute employer/client code, credentials, logs, runbooks, datasets, or architecture material.

## Roadmap

The public direction is:

1. Local, deterministic diagnosis of synthetic incidents.
2. Local incident memory and retrieval.
3. Optional model-provider integrations behind a narrow interface.
4. Framework lifecycle interfaces and reproducible synthetic context.
5. Later, opt-in cookbook examples such as Agno with OpenRouter.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening an issue or pull request. Please also follow the [Code of Conduct](CODE_OF_CONDUCT.md) and report security issues through [SECURITY.md](SECURITY.md).

## License

OpenARIA is licensed under the [Apache License 2.0](LICENSE).
