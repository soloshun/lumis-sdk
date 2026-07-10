# ML regression monitoring cookbook

This cookbook teaches how to use OpenARIA around one bounded machine-learning problem: a synthetic housing-price regression pipeline. It is not a general MLOps platform, a real-estate model, or a production deployment guide. Its purpose is to make three common ML incident shapes reviewable with the same framework used by the data-pipeline cookbook.

## What you will learn

- How a known **feature-distribution drift** signal can be handled by a project-owned deterministic rule without calling an LLM.
- How an unfamiliar **feature-contract failure** can be investigated through bounded telemetry, schema context, and a synthetic inference file.
- How a **candidate-model quality regression** can be investigated without promoting or retraining a model.
- How OpenARIA separates a framework configuration, synthetic ML assets, runbooks, playbooks, an optional Agno/OpenRouter agent, and local incident memory.

Every input in this cookbook is synthetic. The tiny CSV and regression code are included so you can see the sort of model artifact and feature contract an investigation might inspect; they are deliberately dependency-free and are not a real trained model.

## Cookbook layout

```text
ml-regression-monitoring/
├── openaria/                 # Framework configuration for this cookbook
│   ├── openaria.yml          # Project, memory, report, and rule locations
│   └── rules.yml             # Deterministic signatures and their meaning
├── synthetic_project/
│   ├── data/housing_train.csv
│   └── src/                  # Tiny training and inference fixtures
├── knowledge/                # Project-owned runbooks and playbooks
├── demo_service.py           # Read-only synthetic incident estate
└── run_agent.py              # Optional bounded Agno/OpenRouter application
```

The `openaria/` directory is analogous to an infrastructure configuration directory: it holds the framework-facing declaration, not the data, code, or provider credentials. Its paths point back to this cookbook's local `.openaria/` state so reports and SQLite memory remain clearly local to the example.

## Setup

From this cookbook directory:

```bash
uv sync
cp .env.example .env
```

Start the read-only synthetic service in one terminal:

```bash
uv run uvicorn demo_service:app --reload
```

In a second terminal, run one scenario below.

## Scenario 1: known feature drift (deterministic)

```bash
uv run python run_agent.py --incident-id feature-drift-001
```

The synthetic monitor reports `income z_score=4.2 exceeded threshold=3.0`. Both markers match the rule in `openaria/rules.yml`, so OpenARIA writes `.openaria/reports/feature-drift-001-deterministic.md` and local SQLite memory. No model provider or API key is needed.

The rule's `confidence: 0.75` is **not** a probability calculated by OpenARIA, and it is not a claim that the root cause is proven. It is a human-authored calibration value: the rule author is saying the available signature is fairly suggestive of feature-distribution drift, while still requiring the listed missing evidence before any response. Choose a value based on the specificity and reliability of the evidence behind that rule; revise it as your incident history shows whether the rule is trustworthy.

## Scenario 2: unknown feature contract (LLM investigation)

```bash
export OPENROUTER_API_KEY="..."
export OPENARIA_DEMO_MODEL="deepseek/deepseek-v4-flash"
uv run python run_agent.py --incident-id feature-contract-001
```

The log says the prediction path expected three features but received two. It intentionally does not match a deterministic rule. The agent can retrieve the incident's schema context and inspect `synthetic_project/src/inference.py`, which declares the expected feature contract. It must write its final Markdown analysis through `export_analysis` to `.openaria/reports/feature-contract-001-llm.md`.

The agent can investigate and recommend a safe next step. It cannot change an API contract, backfill data, retrain, or deploy a model.

## Scenario 3: candidate quality regression (LLM investigation)

```bash
export OPENROUTER_API_KEY="..."
uv run python run_agent.py --incident-id model-regression-001
```

The synthetic candidate model has validation RMSE 12.8 against an acceptance threshold of 8.0. The agent may read the model-performance runbook and the tiny training fixture. The candidate has not been promoted; the appropriate output is an evidence-grounded investigation and human escalation, not a model change.

## What the agent can and cannot do

The opt-in agent has only named, read-only tools for incident metadata, individual context items, selected knowledge documents, and allowlisted synthetic source/data files. It can store a diagnosis in local SQLite memory and export final Markdown. It has no shell, unrestricted web access, cloud credentials, model registry write access, training trigger, deployment capability, or remediation tool.

OpenRouter is optional and is used only for the two unknown scenarios when you explicitly provide `OPENROUTER_API_KEY`. Do not place real credentials, customer data, model artifacts, or production telemetry in this cookbook.

## How this uses OpenARIA

The cookbook owns the synthetic FastAPI service, regression fixtures, knowledge library, Agno agent, and provider choice. OpenARIA core supplies the configuration loader, deterministic rule evaluator, incident model, redaction boundary, Markdown reporting, SQLite memory, and lifecycle concepts. This division is what lets another project use a different agent framework, model provider, or telemetry source without changing the core framework.
