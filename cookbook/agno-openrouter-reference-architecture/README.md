# Agno + OpenRouter reference-architecture cookbook

This is a separate application that uses OpenARIA's framework ideas to demonstrate the paper’s seven-layer architecture with synthetic context. It does not add FastAPI, Agno, or OpenRouter as OpenARIA core dependencies.

## What it demonstrates

- A manually started FastAPI service simulates the pipeline estate, telemetry, lineage, verification context, and a separate Markdown knowledge library.
- An Agno agent uses OpenRouter only when `OPENROUTER_API_KEY` is explicitly set.
- The agent has bounded tools for `get_incident`, `get_context`, `get_framework_diagnosis`, `read_runbook`, `read_playbook`, `record_framework_diagnosis`, `propose_playbook`, and `request_approval`.
- `get_framework_diagnosis` runs the cookbook's `openaria.yml` and `rules.yml` through OpenARIA, proving that the application uses the framework rather than hardcoding a diagnosis rule in the agent.
- The agent may investigate and propose the synthetic allowlisted playbook, but it cannot execute an action.
- The proposed schema change requires human approval; verification remains `not_run` because no remediation runs.

## Setup

From this cookbook directory:

```bash
uv sync
cp .env.example .env
```

Set `OPENROUTER_API_KEY` in your shell or `.env` loader of choice. Never commit it.

Start the synthetic service in one terminal:

```bash
uv run uvicorn demo_service:app --reload
```

In another terminal, run the opt-in agent:

```bash
export OPENROUTER_API_KEY="..."
export OPENARIA_DEMO_MODEL="openai/gpt-4o-mini"
uv run python run_agent.py
```

For `schema-drift-001`, the cookbook's configured deterministic rule matches first. OpenARIA saves that deterministic report locally and does not call the LLM. For an unknown incident, the agent inspects telemetry and project knowledge; reads code when relevant; and must export its final Markdown through the explicit `export_analysis` tool.

For the intentionally unfamiliar incident, run:

```bash
uv run python run_agent.py --incident-id code-error-001
```

This incident does not match the cookbook's deterministic rule. The agent can call `read_synthetic_code` to inspect the synthetic source file, then must call `export_analysis` exactly once to save its final Markdown analysis under `.openaria/reports/` and local incident memory.

## Knowledge library

The cookbook stores project knowledge separately from telemetry:

- `knowledge/runbooks/schema-drift-investigation.md` explains how to investigate a schema drift incident.
- `knowledge/playbooks/schema_mismatch_in_dataframe.md` defines the allowlisted recommendation and its approval boundary.

The FastAPI service exposes each document through a bounded read-only endpoint. This models how a real project can keep runbooks and playbooks in version-controlled Markdown while giving an agent only the documents it needs.

## Safety boundary

All data is synthetic. The service has no write endpoint. The agent has no shell, unrestricted web-search, cloud, database, or remediation tool. Live model calls are opt-in and must not run in CI.

## Relation to OpenARIA

The cookbook owns the FastAPI service, synthetic data, and Agno/OpenRouter integration. OpenARIA remains the reusable framework that provides the incident, diagnosis, configuration, memory, report, and lifecycle contracts used by future cookbook adapters.
