# OpenARIA

**Vendor-agnostic, guarded self-healing for data, ML, and software delivery pipelines.**

OpenARIA is an open-source, clean-room framework for turning failed data, machine learning, and software delivery pipelines into structured incident reports, evidence-grounded diagnoses, safe recommended next steps, and reusable operational memory.

OpenARIA v0.1 focuses on **Diagnosis-as-Code**. It does not perform automatic production remediation.

## What Diagnosis-as-Code means

Diagnosis-as-Code is OpenARIA's name for making incident diagnosis reproducible, inspectable, and structured instead of leaving it as scattered log reading or tribal knowledge. A failure is converted into a normalized incident, observed evidence, an explicitly uncertain root-cause hypothesis, missing context, and safe next steps.

The output is deliberately reviewable: it distinguishes facts from hypotheses and records the evidence behind each claim. Diagnosis-as-Code is not automatic remediation. In v0.1, OpenARIA recommends what an engineer should investigate; it does not execute production actions.

## Status

OpenARIA is an early proof of concept. The first public proof is a local command that diagnoses a synthetic pipeline failure and produces a Markdown incident report.

## Development

OpenARIA uses [uv](https://docs.astral.sh/uv/) to manage Python and dependencies. Python 3.11 or newer is required.

```bash
uv sync --all-groups
uv run openaria --help
uv run pytest
```

## Try a deterministic diagnosis

The first example is intentionally narrow and offline. It recognizes a synthetic schema-mismatch log and writes an evidence-grounded report:

```bash
uv run openaria diagnose \
  --log examples/simple-log-diagnosis/failure.log
```

The command writes `.openaria/reports/incident-report.md` and stores the incident in local SQLite memory. It uses no external network service, LLM, or remediation action.

## Local incident memory

Each diagnosis is saved in local SQLite memory at `.openaria/incidents.db`. The command prints an incident ID that can be used to retrieve the report, save a final resolution, or find matching past incidents:

```bash
uv run openaria report <incident-id>
uv run openaria resolve <incident-id> --resolution "The source renamed Close to closing_price."
uv run openaria memory search "KeyError Close"
```

Search is local, transparent keyword matching. It does not send incident data anywhere.

## Optional model assistance

The core includes a provider-neutral model boundary that is disabled by default. If a future integration is enabled, OpenARIA minimizes and redacts the log context before it reaches the gateway, validates the structured response against the same diagnosis schema, and falls back to deterministic diagnosis when no model gateway is configured or the response is invalid.

The core does not require an LLM provider or agent framework. Provider-specific examples, including the planned Agno + OpenRouter cookbook, remain opt-in and separate from the core package.

## Safety and clean-room policy

Use only public knowledge, original code, public documentation, and synthetic examples. Do not contribute employer/client code, credentials, logs, runbooks, datasets, or architecture material.

## Roadmap

The public direction is:

1. Local, deterministic diagnosis of synthetic incidents.
2. Local incident memory and retrieval.
3. Optional model-provider integrations behind a narrow interface.
4. Reproducible synthetic pipeline demos.
5. Later, opt-in cookbook examples such as Agno with OpenRouter.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening an issue or pull request. Please also follow the [Code of Conduct](CODE_OF_CONDUCT.md) and report security issues through [SECURITY.md](SECURITY.md).

## License

OpenARIA is licensed under the [Apache License 2.0](LICENSE).
