# Software delivery CI investigation cookbook

This cookbook teaches how Lumis SDK can investigate a bounded software-delivery estate: one synthetic checkout service with CI, release workflow, and Terraform validation failures. It does not connect to GitHub, a cloud account, or a real repository.

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

`uv sync` deliberately installs the repository checkout as an editable local `lumis-sdk` dependency. This keeps the cookbook self-contained for readers who clone the repository. A consuming project can instead use the released PyPI package with `uv add lumis-sdk`.

## Why this cookbook exists

This is an executable research demonstration: a deliberately small application showing how Lumis SDK can be composed around CI and infrastructure incident evidence. It is not a production delivery control plane or an autonomous deployment/remediation system.

Read `run_agent.py` first. It has only three steps: build bounded tools, save a deterministic result when a rule matches, or start the optional agent for an unknown incident. `investigation_tools.py` documents the individual read, report, memory, and approval-boundary capabilities.

## Agno toolkit pattern

This cookbook uses an [Agno custom toolkit](https://docs.agno.com/tools/creating-tools/toolkits): `SoftwareDeliveryTools` inherits from `Toolkit`, retains shared cookbook state, and passes its intentionally allowed bound methods to `super().__init__(tools=[...])`. Agno then registers those methods as the toolkit's tools, so the agent receives the toolkit with `tools=[tools]` rather than a long list in `run_agent.py`.

This is deliberately different from the data-pipeline and ML cookbooks. Those pass bound methods directly to `Agent`, which is a clean choice for a small, one-off tool collection. A custom toolkit is useful when related tools share state and should be reusable, named, filtered, or configured together. It does **not** expose every public method automatically: keeping the list in the toolkit constructor makes the agent's authority explicit, while helper methods such as `diagnosis_for` remain unavailable to the model. In both patterns, method names and docstrings become the tool contract the model sees.

Run one scenario in a second terminal.

### 1. Lockfile mismatch (deterministic)

```bash
uv run python run_agent.py --incident-id lockfile-ci-001
```

The synthetic CI log contains both `lockfile is out of date` and `uv sync --locked`, matching `lumis/rules.yml`. Lumis SDK writes `.lumis/reports/lockfile-ci-001.md` and local SQLite memory without an LLM.

### 2. Release workflow permission failure (LLM investigation)

```bash
export OPENROUTER_API_KEY="..."
export LUMIS_DEMO_MODEL="deepseek/deepseek-v4-flash"
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

The agent receives a production-style software-delivery incident policy: use authorized evidence, distinguish facts from hypotheses, state missing evidence, keep sensitive context redacted, and retain human approval for consequential changes. For an unknown incident, it first retrieves `get_investigation_guide`, which supplies the valid context keys, workflow/source paths, runbooks, and playbooks for that scenario. The tool parameter schemas also restrict requests to the cookbook's valid identifiers. Agno receives the documented `SoftwareDeliveryTools` toolkit; the model chooses relevant read-only evidence rather than following a scripted sequence or guessing resource names.

For unknown incidents, Agno streams the investigation in the terminal. Before completing, the agent calls `export_analysis` with a simple incident-specific Markdown filename and the complete report text. The tool writes only inside the cookbook's report directory, then records the report in local memory. All incidents, code, workflows, and infrastructure configuration in this cookbook are synthetic.

## Layout

```text
software-delivery-ci-investigation/
├── lumis/                 # project configuration and deterministic rules
├── synthetic_project/        # fake workflow, source, and Terraform files
├── knowledge/                # investigation runbooks and proposed playbook
├── demo_service.py           # read-only synthetic incident estate
├── investigation_tools.py    # bounded, documented agent capabilities
└── run_agent.py              # small deterministic-first application entry point
```

Lumis SDK core remains vendor-agnostic: the cookbook owns its CI terminology, synthetic files, FastAPI service, rules, prompts, and provider integration. The runner imports local implementations from `lumis_sdk.adapters`, project declarations from `lumis_sdk.config`, and redaction from `lumis_sdk.security`. A real project could replace GitHub Actions, GitLab CI, Azure DevOps, IaC tooling, or the agent/model framework without changing the domain and port contracts.
