<h1 align="center">Lumis SDK</h1>

<p align="center">
  <strong>Deterministic-first, evidence-grounded incident recovery for data, ML, and software pipelines.</strong>
</p>

<p align="center">
  <a href="https://github.com/soloshun/lumis-sdk/actions">CI</a> ·
  <a href="LICENSE">Apache-2.0</a> ·
  <a href="docs/architecture/overview.md">Architecture</a> ·
  <a href="docs/configuration.md">Configuration</a> ·
  <a href="cookbook/README.md">Cookbooks</a> ·
  <a href="ROADMAP.md">Roadmap</a>
</p>

Lumis SDK is an open-source Python implementation companion to the **agentic recovery and incident response** reference architecture proposed in the accompanying research. It provides reusable contracts and local reference adapters for diagnosing failures in data, machine-learning, and software-delivery pipelines while keeping models optional and consequential actions under explicit control.

Lumis SDK starts with Diagnosis-as-Code: bounded incident evidence becomes a structured,
reviewable diagnosis, Markdown or JSON report, and operational-memory record. Its direction is
Healing-as-Code: a guarded lifecycle for detect, triage, diagnose, plan, approve, remediate,
verify, and learn.

> **Pre-alpha:** Lumis SDK does not perform unrestricted or default production remediation. Current execution-related models are recommendation and verification contracts, not an authority granted to an LLM.

## Research and implementation boundary

| Artefact | Role | Repository boundary |
| --- | --- | --- |
| **Reference architecture** | Agentic recovery and incident response lifecycle. | Technology-flexible design described by the paper. |
| **Lumis SDK** | Apache-2.0 framework and local implementation companion. | Domain contracts, application services, ports, safe reference adapters, CLI, testkit, and cookbooks. |


## Design principles

- **Deterministic first.** Known signatures and project rules run before optional model reasoning.
- **Evidence grounded.** Facts, evidence, hypotheses, confidence, contradictions, and missing evidence remain distinguishable.
- **Model optional.** The core works offline; provider integrations implement a narrow gateway port.
- **Local first.** SQLite and Markdown are inspectable defaults, not mandatory hosted services.
- **Guarded recovery.** Plans are allowlisted recommendations; approval and verification are explicit boundaries.
- **Confirmed memory.** Model output is never silently promoted into confirmed operational truth.
- **Vendor agnostic.** Domain and application packages import no observability, orchestration, cloud, or agent SDK.

## Architecture

```mermaid
flowchart LR
    subgraph USERS[Project entry points]
        CLI[Lumis SDK CLI]
        PY[Python application]
    end
    subgraph CORE[Lumis SDK framework]
        CFG[Strict project and rule configuration]
        APP[Application services]
        DOMAIN[Domain contracts]
        PORTS[Optional provider ports]
    end
    subgraph LOCAL[Local reference adapters]
        DET[Deterministic diagnosis]
        MEM[SQLite incident memory]
        EVIDENCE[Bounded local JSON evidence]
        REPORT[Markdown and JSON reports]
        REDACT[Evidence redaction]
    end

    CLI --> CFG
    CLI --> DET
    CLI --> EVIDENCE
    CLI --> MEM
    CLI --> REPORT
    PY --> APP
    APP --> DOMAIN
    APP --> PORTS
    APP --> DET
    CFG --> DET
    EVIDENCE --> PORTS
    REDACT --> PORTS
```

Canonical package boundaries:

```text
src/lumis_sdk/
├── domain/       # strict vendor-neutral models
├── application/  # use-case orchestration
├── ports/        # replaceable provider interfaces
├── adapters/     # deterministic, SQLite, evidence, report, and local adapters
├── config/       # versioned strict configuration
├── cli/          # command composition
├── security/     # redaction and evidence-safety utilities
└── testkit/      # deterministic test doubles
```

The proof-of-concept flat modules have been removed. New code imports the explicit domain, application, port, adapter, configuration, and security packages shown above.

Read the [architecture overview](docs/architecture/overview.md), [SDK reference](docs/LUMIS_SDK_REFERENCE.md), and [configuration reference](docs/configuration.md).
The [structured-rules API guide](docs/python-api/structured-rules.md) covers compound incident
fields, evidence, fixture testing, and migration from `all_contains`.
The [evidence and JSON reports guide](docs/python-api/evidence-and-json-reports.md) documents the
provider contract, bounded collection behavior, report schema, and reusable testkit.

## Current capabilities

| Capability | Current behavior |
| --- | --- |
| Incident input | Local log normalization and typed vendor-neutral incident contracts. |
| Evidence collection | Async provider port, bounded collection service, safe failures, redaction, and a local JSON reference adapter. |
| Deterministic diagnosis | Legacy ordered text rules plus structured `all`/`any`/`not` rules with typed comparisons, required evidence, ranking, and candidate explanations. |
| Versioned configuration | Strict `lumis.dev/v1alpha1` project and rule-set documents; unknown fields fail validation. |
| Reports | Deterministic Markdown or versioned JSON with facts, evidence, hypotheses, truth state, confidence, review requirement, and safety boundary. |
| Local memory | SQLite records, human resolutions, visible truth state, and transparent lexical search. |
| Model boundary | Explicit policy, budgets, schema-validated output, fake CI gateway, and deterministic fallback. |
| Guarded lifecycle | Context, policy, approval, verification, and audit ports with no core action executor. |
| CLI | Initialization, diagnosis, doctor, rule validation, reports, resolution, and memory search. |
| Cookbooks | Synthetic data, ML regression, and software-delivery investigations with optional Agno/OpenRouter paths. |

## Quick start

Lumis SDK supports Python 3.11+ and uses [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/soloshun/lumis-sdk.git
cd lumis-sdk
uv sync --all-groups
uv run lumis --help
```

## Install Lumis SDK

Lumis SDK is published to PyPI as `lumis-sdk`. Add it to a project managed by `uv`:

```bash
uv add "lumis-sdk>=0.0.1,<0.1.0"
```

Or install it into an existing environment with pip:

```bash
pip install lumis-sdk
```

For a specific reproducible release, pin the version:

```bash
uv add "lumis-sdk==0.0.3"
pip install "lumis-sdk==0.0.3"
```

The repository's GitHub Actions workflow publishes reviewed releases through PyPI Trusted Publishing.

Run the local deterministic example:

```bash
uv run lumis doctor \
  --config cookbook/simple-log-diagnosis/lumis/lumis.yml

uv run lumis diagnose \
  --config cookbook/simple-log-diagnosis/lumis/lumis.yml
```

The command reads a synthetic local log, writes a Markdown report, saves an unconfirmed incident episode to local SQLite, and prints its incident ID. It makes no network or model call.

```bash
uv run lumis report <incident-id> \
  --config cookbook/simple-log-diagnosis/lumis/lumis.yml

uv run lumis resolve <incident-id> \
  --resolution "Human-confirmed cause, action, and outcome." \
  --config cookbook/simple-log-diagnosis/lumis/lumis.yml

uv run lumis memory search "KeyError Close" \
  --config cookbook/simple-log-diagnosis/lumis/lumis.yml
```



## Versioned project configuration

```yaml
apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: customer-pipeline
spec:
  environment: local
  memory:
    provider: sqlite
    path: .lumis/incidents.db
  reports:
    provider: markdown
    outputDir: .lumis/reports
  incidentSources:
    - provider: local-log
      path: logs/latest-failure.log
  evidenceProviders:
    - provider: local-json
      path: evidence/schema-diff.json
      kinds: [schema-diff]
      maxItems: 20
      maxTotalCharacters: 50000
  rules:
    files: [rules.yml]
  model:
    enabled: false
```

Configuration is strict: misspelled or unknown fields fail with a validation error. Relative paths resolve from the project document. Files larger than the configured safety limit are rejected. Checked schemas for the [project](schemas/lumis-project-v1alpha1.schema.json), [rule set](schemas/lumis-rules-v1alpha1.schema.json), [structured diagnosis rule](schemas/lumis-diagnosis-rule-v1alpha1.schema.json), and [JSON diagnosis report](schemas/lumis-diagnosis-report-v1alpha1.schema.json) support editors and tooling.

Lumis SDK intentionally accepts only the versioned project and rule-set structures during this pre-release revamp. Read the [configuration reference](docs/configuration.md) for every field and its meaning.

## CLI

```text
lumis init
lumis doctor
lumis diagnose
lumis report
lumis resolve
lumis memory search
lumis rules validate
lumis rules test
```

`doctor` and validation commands do not make network calls or write incident state. Model assistance remains disabled unless application code supplies both an enabled policy and a gateway adapter.

## Python API

```python
import asyncio
from pathlib import Path

from lumis_sdk.application import DiagnosisService
from lumis_sdk.config import load_config
from lumis_sdk.domain import IncidentInput

config = load_config(Path("lumis.yml"))
service = DiagnosisService(rules=config.rules)
incident = IncidentInput(
    source_tool="local-log",
    pipeline_name=config.project,
    raw_payload={"log": "ERROR KeyError: Close"},
)
diagnosis = asyncio.run(service.diagnose(incident))
```

## Cookbooks

- [Simple local diagnosis](cookbook/simple-log-diagnosis/README.md)
- [Data pipeline investigation](cookbook/data-pipeline-investigation/README.md)
- [ML regression monitoring](cookbook/ml-regression-monitoring/README.md)
- [Software-delivery CI investigation](cookbook/software-delivery-ci-investigation/README.md)
- [Structured rule evaluation](cookbook/structured-rule-evaluation/README.md)
- [Evidence collection and JSON reporting](cookbook/evidence-json-reporting/README.md)
- [Recording a human resolution](cookbook/recording-resolution/README.md)

Start with a cookbook for a runnable demonstration, then use the architecture and core references above to examine the framework contracts behind it. All examples are synthetic, executable research demonstrations: they show how a consuming application can use Lumis SDK without claiming to be production control planes or autonomous remediation systems. Agent frameworks and model providers remain cookbook-only optional dependencies.

## Safety

Lumis SDK treats logs, tickets, runbooks, source files, and model output as untrusted input.

- No direct shell, cloud-admin, Kubernetes-admin, or database actuation in core.
- No live model key or billable request in CI.
- No telemetry export by default.
- Bounded configuration and log reads.
- Conservative redaction before optional model use.
- Model output remains an unconfirmed hypothesis until a human or verifier confirms it.
- Execution capability requires a future RFC, allowlisted typed actions, policy, approval, audit, limits, and verification.

Read the [threat model](docs/safety/threat-model.md) and [security policy](SECURITY.md).

## Development

```bash
uv sync --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/generate_config_schema.py --check
uv run pytest
uv build
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md), [SUPPORT.md](SUPPORT.md), [CHANGELOG.md](CHANGELOG.md), and [ROADMAP.md](ROADMAP.md).

## Releases

Lumis SDK releases are manually dispatched through GitHub Actions and published with PyPI Trusted Publishing.

## Research and standards context

Lumis SDK is informed by [OpenTelemetry](https://opentelemetry.io/), [OpenLineage](https://openlineage.io/), [Prometheus](https://prometheus.io/), [Site Reliability Engineering](https://sre.google/sre-book/table-of-contents/), [ReAct](https://arxiv.org/abs/2210.03629), and [LLM-based incident RCA research](https://doi.org/10.1145/3627703.3629553). These are design influences, not mandatory dependencies or claims of conformance.

## Maintainer and license

Lumis SDK is currently maintained by [Solomon Eshun](mailto:solomoneshun373@gmail.com) and licensed under [Apache License 2.0](LICENSE).
