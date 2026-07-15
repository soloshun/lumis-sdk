# Data pipeline investigation cookbook

This cookbook teaches how Lumis SDK can investigate a bounded synthetic data-pipeline incident estate. It uses schema, lineage, telemetry, code, and knowledge context to demonstrate the paper’s architecture without turning FastAPI, Agno, or OpenRouter into Lumis SDK core dependencies.

It is deliberately a **data-pipeline** example, not a generic demonstration of every kind of data incident. The next cookbook, `ml-regression-monitoring`, covers a separate ML regression domain.

## What you will learn

- How a known schema-drift signature is handled deterministically from `lumis/rules.yml`.
- How an unfamiliar transformation error can route to an opt-in agent that reads bounded synthetic code.
- How sensitive values in telemetry are redacted before agent tools and reports receive them.
- How runbooks and playbooks remain project-owned Markdown knowledge, separate from telemetry and framework code.

## Cookbook layout

```text
data-pipeline-investigation/
├── lumis/                 # Framework configuration and deterministic rules
├── synthetic_project/        # Bounded code fixture for the unfamiliar-error scenario
├── knowledge/                # Cookbook-owned runbook and playbook Markdown
├── demo_service.py           # Read-only synthetic incident estate
├── investigation_tools.py    # Bounded, documented agent capabilities
└── run_agent.py              # Small deterministic-first application entry point
```

The `lumis/` directory is the cookbook's framework configuration boundary. `lumis.yml` points to local state and `rules.yml` defines the project-specific signatures; data, code, and provider integration remain outside it.

`uv sync` deliberately installs the repository checkout as an editable local `lumis-sdk` dependency. This keeps the cookbook self-contained and lets a reader inspect or change the framework while running the example. A consuming project can instead use the PyPI package with `uv add lumis-sdk`.

## Why this cookbook exists

This is an executable research demonstration: a deliberately small application that shows how Lumis SDK can be composed around an evidence-grounded incident flow. It is not a production control plane, monitoring platform, or autonomous remediation system.

Read `run_agent.py` first. It has only three steps: build the bounded tools, save a deterministic result when a rule matches, or start the optional agent for an unknown incident. `investigation_tools.py` documents each read, report, memory, and approval-boundary capability individually.

## What it demonstrates

- A manually started FastAPI service simulates the pipeline estate, telemetry, lineage, verification context, and a separate Markdown knowledge library.
- An Agno agent uses OpenRouter only when `OPENROUTER_API_KEY` is explicitly set.
- The agent has bounded tools for incident/context retrieval, framework diagnosis, runbook/playbook and synthetic-code reads, approval requests, and one safe Markdown-report export capability.
- `get_framework_diagnosis` runs the cookbook's `lumis/lumis.yml` and `lumis/rules.yml` through Lumis SDK, proving that the application uses the framework rather than hardcoding a diagnosis rule in the agent.
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

The `KeyError: 'Close'` signature matches `rules.yml`. Lumis SDK writes `.lumis/reports/schema-drift-001.md` and a local SQLite memory record. No LLM request is made.

### 2. Unfamiliar code error (LLM investigation)

```bash
export OPENROUTER_API_KEY="..."
export LUMIS_DEMO_MODEL="deepseek/deepseek-v4-flash"
uv run python run_agent.py --incident-id code-error-001
```

This incident has an unfamiliar `adjusted_price` error, so the agent can inspect `synthetic_project/src/price_transform.py`. Agno streams the investigation and formats it in the terminal. Before completing, the agent calls `export_analysis` with `report_name="code-error-001-llm.md"` and the complete Markdown report. The tool writes that report to `.lumis/reports/` and records it in local SQLite memory.

### 3. Sensitive data in telemetry (LLM investigation with redaction)

```bash
export OPENROUTER_API_KEY="..."
uv run python run_agent.py --incident-id pii-leak-001
```

This synthetic incident contains an email address, API key, phone number, SSN, and test card number in its source telemetry. The FastAPI service models an unsafe upstream payload; it is not what the model sees. Lumis SDK redacts JSON-like tool responses before the agent receives them, so the agent sees markers such as `[REDACTED_EMAIL]` and `[REDACTED_SECRET]`, and its final report is saved as `.lumis/reports/pii-leak-001-llm.md`.

Do not place real credentials or personal data in this cookbook. The redactor is a conservative demonstration baseline, not a complete organization-specific DLP system.

## How the investigation flows

1. `run_agent.py` first runs the cookbook's `lumis/lumis.yml` and `lumis/rules.yml` through Lumis SDK's deterministic diagnosis engine.
2. A rule match produces the deterministic report immediately. An unknown diagnosis requires an explicitly configured OpenRouter call.
3. The agent receives a production-style incident-response policy: evidence and uncertainty standards, confidentiality constraints, report requirements, approval boundaries, and prohibited actions.
4. For an unknown incident, the agent first retrieves `get_investigation_guide`. The guide returns the exact available context keys, source paths, runbooks, and playbooks for that incident. Tool parameter schemas also restrict requests to the cookbook's valid identifiers, so the model does not need to guess names.
5. Agno converts the documented `DataPipelineTools` methods into tool definitions. The model then chooses which of the guide's read-only incident, context, knowledge, or code capabilities is relevant; the cookbook does not prescribe a fixed evidence sequence.
6. The agent may recommend a playbook and request human approval, but has no execution tool. For an LLM scenario, it must call `export_analysis` exactly once with a simple Markdown filename and the complete final report text before presenting that same report in the terminal.

## Knowledge library

The cookbook stores project knowledge separately from telemetry:

- `knowledge/runbooks/schema-drift-investigation.md` explains how to investigate a schema drift incident.
- `knowledge/playbooks/schema_mismatch_in_dataframe.md` defines the allowlisted recommendation and its approval boundary.

The FastAPI service exposes each document through a bounded read-only endpoint. This models how a real project can keep runbooks and playbooks in version-controlled Markdown while giving an agent only the documents it needs.

## Safety boundary

All data is synthetic. The service has no write endpoint. The agent has no shell, unrestricted web-search, cloud, database, or remediation tool. Sensitive values are redacted before context reaches an agent tool or framework diagnostic report. Live model calls are opt-in and must not run in CI.

## Relation to Lumis SDK

The cookbook owns the FastAPI service, synthetic data, rules, knowledge, prompts, and Agno/OpenRouter integration. Its application imports deterministic and local-log behavior from `lumis_sdk.adapters`, strict project declarations from `lumis_sdk.config`, typed contracts from `lumis_sdk.domain`, and redaction from `lumis_sdk.security`. This is the same canonical surface available to any consuming project; no deprecated proof-of-concept modules are involved.
