# OpenARIA

**Vendor-agnostic, guarded self-healing for data, ML, and software delivery pipelines.**

OpenARIA is an open-source, clean-room framework for turning failed data, machine learning, and software delivery pipelines into structured incident reports, evidence-grounded diagnoses, safe recommended next steps, and reusable operational memory.

OpenARIA v0.1 focuses on **Diagnosis-as-Code**. It does not perform automatic production remediation.

## Status

OpenARIA is an early proof of concept. The first public proof is a local command that diagnoses a synthetic pipeline failure and produces a Markdown incident report.

## Development

OpenARIA uses [uv](https://docs.astral.sh/uv/) to manage Python and dependencies. Python 3.11 or newer is required.

```bash
uv sync --all-groups
uv run openaria --help
uv run pytest
```

## First deterministic diagnosis

Sprint 1 contains one intentionally narrow, offline proof. It recognizes a synthetic schema-mismatch log and writes an evidence-grounded report:

```bash
uv run openaria diagnose \
  --log examples/simple-log-diagnosis/failure.log
```

The command writes `.openaria/reports/incident-report.md` by default. It uses no network service, LLM, database, or remediation action.

## Local incident memory

Sprint 2 saves each diagnosis in local SQLite memory at `.openaria/incidents.db`. The command prints an incident ID that can be used to retrieve the report, save a final resolution, or find matching past incidents:

```bash
uv run openaria report <incident-id>
uv run openaria resolve <incident-id> --resolution "The source renamed Close to closing_price."
uv run openaria memory search "KeyError Close"
```

Search is local, transparent keyword matching. It does not send incident data anywhere.

## Safety and clean-room policy

Use only public knowledge, original code, public documentation, and synthetic examples. Do not contribute employer/client code, credentials, logs, runbooks, datasets, or architecture material.

## Roadmap

The internal sprint tracker is intentionally not part of the public repository. The public direction is:

1. Local, deterministic diagnosis of synthetic incidents.
2. Local incident memory and retrieval.
3. Optional model-provider integrations behind a narrow interface.
4. Reproducible synthetic pipeline demos.
5. Later, opt-in cookbook examples such as Agno with OpenRouter.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening an issue or pull request. Please also follow the [Code of Conduct](CODE_OF_CONDUCT.md) and report security issues through [SECURITY.md](SECURITY.md).

## License

OpenARIA is licensed under the [Apache License 2.0](LICENSE).
