# Software delivery CI investigation cookbook

This cookbook teaches how OpenARIA can investigate a bounded software-delivery estate: one synthetic checkout service with CI, release workflow, and Terraform validation failures. It does not connect to GitHub, a cloud account, or a real repository.

## What you will learn

- How a known lockfile mismatch is handled deterministically with no model call.
- How an unfamiliar CI authorization failure can be investigated from bounded workflow context.
- How an unfamiliar infrastructure reference failure can be investigated from bounded Terraform context.
- How a recommendation-only agent can discuss a reviewable change without pushing code, changing permissions, running Terraform, or creating resources.

## Setup

From this cookbook directory:

```bash
uv sync
uv run uvicorn demo_service:app --reload
```

Run one scenario in a second terminal.

### 1. Lockfile mismatch (deterministic)

```bash
uv run python run_agent.py --incident-id lockfile-ci-001
```

The synthetic CI log contains both `lockfile is out of date` and `uv sync --locked`, matching `openaria/rules.yml`. OpenARIA writes `.openaria/reports/lockfile-ci-001-deterministic.md` and local SQLite memory without an LLM.

### 2. Release workflow permission failure (LLM investigation)

```bash
export OPENROUTER_API_KEY="..."
export OPENARIA_DEMO_MODEL="deepseek/deepseek-v4-flash"
uv run python run_agent.py --incident-id workflow-permission-001
```

The agent can inspect the bounded synthetic release workflow and permission-investigation runbook. It should identify evidence and propose the smallest reviewable permission change, but cannot alter a workflow or claim that a release was published.

### 3. Terraform undeclared-resource failure (LLM investigation)

```bash
export OPENROUTER_API_KEY="..."
uv run python run_agent.py --incident-id infra-resource-001
```

The agent can inspect `synthetic_project/infra/main.tf` and the infrastructure runbook. It can explain the inconsistent resource reference and recommend a reviewed configuration correction. It cannot run a plan or apply, access cloud credentials, or create infrastructure.

## Agent behavior and boundaries

The agent receives a production-style software-delivery incident policy: use authorized evidence, distinguish facts from hypotheses, state missing evidence, keep sensitive context redacted, and retain human approval for consequential changes. Agno exposes functions and docstrings as tool definitions; the model chooses relevant read-only context, runbook, workflow, or infrastructure-file capabilities rather than following a scripted sequence.

For unknown incidents, the final human-readable Markdown analysis is persisted through the available report-recording capability. All incidents, code, workflows, and infrastructure configuration in this cookbook are synthetic.

## Layout

```text
software-delivery-ci-investigation/
├── openaria/                 # project configuration and deterministic rules
├── synthetic_project/        # fake workflow, source, and Terraform files
├── knowledge/                # investigation runbooks and proposed playbook
├── demo_service.py           # read-only synthetic incident estate
└── run_agent.py              # opt-in Agno/OpenRouter application
```

OpenARIA core remains vendor-agnostic: the cookbook owns its CI terminology, synthetic files, FastAPI service, and provider integration. A real project could replace these with GitHub Actions, GitLab CI, Azure DevOps, another IaC tool, or another agent/model framework without changing the core diagnosis, report, memory, and lifecycle contracts.
