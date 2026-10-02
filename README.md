# Lumis SDK

Experimental, open-source Python primitives for **evidence-grounded operational intelligence**.
Data & AI infrastructure is the first focus; GridCast is the synthetic reference estate.

**LLM proposes. Lumis tests against observations.** Models, rules and retrieved precedents produce
the same falsifiable hypotheses. A bounded operational graph, provenance-bearing evidence,
deterministic checks and an inspectable trace make uncertainty explicit.

This is active research, not a production autonomous operator. The read-only MVP has no action
executor. Supported candidates remain `unconfirmed_hypothesis`; support is not causal proof,
a calibrated probability, or permission to change infrastructure.

## Run the new offline slice

Python 3.11–3.13, [uv](https://docs.astral.sh/uv/), no cluster or paid model key needed:

```bash
git clone https://github.com/soloshun/lumis-sdk.git
cd lumis-sdk
git checkout dev
uv sync --all-groups
uv run lumis investigate \
  --project examples/gridcast-readonly/project.yaml \
  --incident examples/gridcast-readonly/incident.json \
  --observations examples/gridcast-readonly/observations.json
```

Expected: three candidate assessments, one supported and two contradicted, four audited queries,
and explicitly unconfirmed truth. This is a **synthetic contract replay**, not a live GridCast
deployment result. [Walkthrough](examples/gridcast-readonly/README.md).

## What is implemented

- Strict entities, relationships, incident windows, queries, observations, falsifiable candidates,
  budgets, terminal investigations and checked JSON Schemas.
- Indexed, cycle-safe graph traversal with explicit hop/entity limits and serialized scoped graphs.
- Declared/discovered topology merging with conflict rejection.
- Namespace-scoped Kubernetes discovery and exported OTLP/JSON service-topology normalization.
- Prometheus instant-query adapter; registered query IDs keep query construction operator-owned.
- Uniform rule, memory and model candidate sources; candidate validation/deduplication.
- Bounded active evidence collection, deterministic support/contradiction and first-class abstention.
- Optional structured OpenRouter generation (3–5 candidates), opt-in network/model use.
- Local SQLite investigation records and machine-readable CLI output.

Live GridCast validation, baseline comparisons, calibrated reasoning, Prefect/Git collectors,
recovery execution and recurrence-to-rule promotion remain [roadmap work](ROADMAP.md).
Existing proposal/approval/verification APIs are preserved, but the new read-only runtime does
not connect them to actuation.

## Architecture and usage

```text
lumis_sdk/
  core/         strict operational contracts
  graph/        indexed bounded topology
  connectors/   external read-only observations/discovery
  reasoning/    uniform sources and mechanical evidence checks
  models/       optional structured providers
  runtime/      scope → propose → seek → assess → retain
  cli/          investigate/discover plus retained legacy commands
```

No GridCast application imports are needed. Deploy Lumis beside an instrumented estate and
connect through APIs, exported telemetry and explicit declarations. No graph database,
agent framework, or hosted Lumis account is mandatory.

- [Architecture and decisions](docs/operational-intelligence/architecture.md)
- [Python API and schemas](docs/operational-intelligence/python-api.md)
- [GridCast integration contract](docs/operational-intelligence/gridcast-integration.md)
- [Roadmap and sprints](ROADMAP.md)
- [0.1.0 release gates](docs/operational-intelligence/release-gates.md)
- [Documentation index](docs/README.md)
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Apache-2.0](LICENSE)

HTTP/model adapters require `lumis-sdk[http]`. For this **unreleased** architecture, install the
reviewed Git revision or build its wheel; the existing PyPI `0.1.0rc1` does not contain it.
The package version is intentionally unchanged until a new RC is qualified.

## Compatibility and research

The pre-reset release is preserved on `legacy/pre-operational-intelligence-2026-10-02`.
Existing `domain/application/ports/adapters` imports and `lumis.dev/v1` documents remain
available for consumers and existing research regressions. New operational documents use
`lumis.dev/operational-v1alpha1`; they are provisional and not drop-in replacements.
[Migration boundary](docs/operational-intelligence/migration.md).
Legacy cookbooks remain tested but are no longer the primary development track.

Lumis began as an implementation companion to
[Agentic Self-Healing for Data & AI Pipelines](https://arxiv.org/abs/2608.01955).
The guarded-control substrate remains relevant; the operational-intelligence work extends the
research direction without claiming empirical superiority or conference acceptance.
[Research alignment](docs/architecture/research-alignment.md).
