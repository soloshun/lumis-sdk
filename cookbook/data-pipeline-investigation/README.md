# Data pipeline investigation cookbook

This cookbook teaches how OpenARIA can investigate a bounded synthetic data-pipeline incident estate. It uses schema, lineage, telemetry, code, and knowledge context to demonstrate the paper’s architecture without turning FastAPI, Agno, or OpenRouter into OpenARIA core dependencies.

It is deliberately a **data-pipeline** example, not a generic demonstration of every kind of data incident. The next cookbook, `ml-regression-monitoring`, covers a separate ML regression domain.

## What you will learn

- How a known schema-drift signature is handled deterministically from `openaria/rules.yml`.
- How an unfamiliar transformation error can route to an opt-in agent that reads bounded synthetic code.
- How sensitive values in telemetry are redacted before agent tools and reports receive them.
- How runbooks and playbooks remain project-owned Markdown knowledge, separate from telemetry and framework code.

## Cookbook layout

```text
data-pipeline-investigation/
├── openaria/                 # Framework configuration and deterministic rules
├── synthetic_project/        # Bounded code fixture for the unfamiliar-error scenario
├── knowledge/                # Cookbook-owned runbook and playbook Markdown
├── demo_service.py           # Read-only synthetic incident estate
└── run_agent.py              # Optional Agno/OpenRouter application
```

The `openaria/` directory is the cookbook's framework configuration boundary. `openaria.yml` points to local state and `rules.yml` defines the project-specific signatures; data, code, and provider integration remain outside it.

## What it demonstrates

- A manually started FastAPI service simulates the pipeline estate, telemetry, lineage, verification context, and a separate Markdown knowledge library.
- An Agno agent uses OpenRouter only when `OPENROUTER_API_KEY` is explicitly set.
- The agent has bounded tools for incident/context retrieval, framework diagnosis, runbook/playbook and synthetic-code reads, local diagnosis recording, approval requests, and final Markdown export.
- `get_framework_diagnosis` runs the cookbook's `openaria/openaria.yml` and `openaria/rules.yml` through OpenARIA, proving that the application uses the framework rather than hardcoding a diagnosis rule in the agent.
- The agent may investigate and propose the synthetic allowlisted playbook, but it cannot execute an action.
- The proposed schema change requires human approval; verification remains `not_run` because no remediation runs.

## Setup

From this cookbook directory:

```bash
uv sync
cp .env.example .env
```

Start the synthetic service in one terminal:

```bash
uv run uvicorn demo_service:app --reload
```

In another terminal, choose one of the scenarios below. The first scenario needs no model key; the other two deliberately bypass the configured deterministic rule and require an OpenRouter key.

### 1. Configured schema drift (deterministic only)

```bash
uv run python run_agent.py --incident-id schema-drift-001
```

The `KeyError: 'Close'` signature matches `rules.yml`. OpenARIA writes `.openaria/reports/schema-drift-001-deterministic.md` and a local SQLite memory record. No LLM request is made.

### 2. Unfamiliar code error (LLM investigation)

```bash
export OPENROUTER_API_KEY="..."
export OPENARIA_DEMO_MODEL="deepseek/deepseek-v4-flash"
uv run python run_agent.py --incident-id code-error-001
```

This incident has an unfamiliar `adjusted_price` error, so the agent can inspect `synthetic_project/src/price_transform.py`. Once it has investigated, it must call `export_analysis` exactly once. That tool writes the final human-readable report to `.openaria/reports/code-error-001-llm.md` and records it in local SQLite memory.

### 3. Sensitive data in telemetry (LLM investigation with redaction)

```bash
export OPENROUTER_API_KEY="..."
uv run python run_agent.py --incident-id pii-leak-001
```

This synthetic incident contains an email address, API key, phone number, SSN, and test card number in its source telemetry. The FastAPI service models an unsafe upstream payload; it is not what the model sees. OpenARIA redacts JSON-like tool responses before the agent receives them, so the agent sees markers such as `[REDACTED_EMAIL]` and `[REDACTED_SECRET]`, and its final report is saved as `.openaria/reports/pii-leak-001-llm.md`.

Do not place real credentials or personal data in this cookbook. The redactor is a conservative demonstration baseline, not a complete organization-specific DLP system.

## How the investigation flows

1. `run_agent.py` first runs the cookbook's `openaria/openaria.yml` and `openaria/rules.yml` through OpenARIA's deterministic diagnosis engine.
2. A rule match produces the deterministic report immediately. An unknown diagnosis requires an explicitly configured OpenRouter call.
3. The agent receives a production-style incident-response policy: evidence and uncertainty standards, confidentiality constraints, report requirements, approval boundaries, and prohibited actions.
4. Agno converts the named Python functions and their docstrings into tool definitions. The model chooses which read-only incident, context, knowledge, or code capability is relevant; the cookbook does not prescribe a fixed tool sequence.
5. The agent may recommend a playbook and request human approval, but has no execution tool. For an LLM scenario, it must persist its final Markdown through the available report-recording capability so the human-readable analysis is not lost in terminal output.

## Knowledge library

The cookbook stores project knowledge separately from telemetry:

- `knowledge/runbooks/schema-drift-investigation.md` explains how to investigate a schema drift incident.
- `knowledge/playbooks/schema_mismatch_in_dataframe.md` defines the allowlisted recommendation and its approval boundary.

The FastAPI service exposes each document through a bounded read-only endpoint. This models how a real project can keep runbooks and playbooks in version-controlled Markdown while giving an agent only the documents it needs.

## Safety boundary

All data is synthetic. The service has no write endpoint. The agent has no shell, unrestricted web-search, cloud, database, or remediation tool. Sensitive values are redacted before context reaches an agent tool or framework diagnostic report. Live model calls are opt-in and must not run in CI.

## Relation to OpenARIA

The cookbook owns the FastAPI service, synthetic data, and Agno/OpenRouter integration. OpenARIA remains the reusable framework that provides the incident, diagnosis, configuration, memory, report, and lifecycle contracts used by future cookbook adapters.
