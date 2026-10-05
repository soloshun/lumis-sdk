# Changelog

## Unreleased

- Documentation only: a high-level "How Lumis works" diagram in the README, plus diagrams for
  responsibility layers, graph preparation, triage routing and how a report reaches its
  conclusion. A [small-project guide](docs/small-project.md) with a tested one-service
  Prometheus example (`docs/examples/small-project/`). No code or API change.

## 0.1.0 — 2026-10-05 (experimental, pre-1.0)

First index release of the standalone operational-intelligence architecture. It replaces the
0.0.x framework and the earlier `0.1.0rc1` upload, which was built from the previous
architecture; see [migration](docs/migration.md). Lumis remains research software: read-only
investigation and human-review reports, no remediation executor.

### Hardening from the GridCast live integration

Each item was observed on the live GridCast reference estate; root causes and commits are in
[the integration lessons](docs/design-notes/gridcast-integration-lessons.md).

- Redaction no longer masks telemetry decimals, epochs, ISO dates and IPv4 addresses. Prometheus
  facts stay inside the incident window; completed Job pods are no longer topology (#105).
- Reference agent: no `parallel_tool_calls`, `validation_retries`, an output validator plus
  per-candidate acceptance, distinct stop reasons (`agent_budget_exhausted`,
  `agent_output_invalid`), `models.reasoning` and `PydanticInvestigator.messages` (#105).
- Read-only SQL evidence provider (`sources.sql`, optional `sql` extra), opt-in commit subjects
  in `git.log`, and typed recent-change records (`sources.changes`, `inspect(changes)`): Git
  commits on operator-mapped paths and Kubernetes rollouts, including re-activations (#105).
- Competing supported root causes are reported as `insufficient_evidence` with the competing
  roots listed, not as a diagnosis; a resource that `hosts` a service counts as that service (#106).
- Registered Loki queries may export up to five allowlisted structured-metadata fields (#107).
- Reports name the exception type and HTTP status that stopped the investigator, never the
  message (#113).
- Offline SDK playground notebook; all three notebooks execute in the test suite (#108).

### Live qualification (separate evidence)

The [GridCast cookbook](https://github.com/soloshun/lumis-cookbooks/tree/main/gridcast) ran this SDK against 15 injected failure scenarios on a live
Kubernetes estate, with deterministic triage, the reference agent and five comparison baselines.
Only DeepSeek v4 pro (through OpenRouter) was evaluated. The native OpenAI, Anthropic and Gemini
adapters are contract-tested with mocked transports only; no live quality claim is made for them.

### Architecture

- Implement YAML-backed optional Loki/Tempo/Prefect read-only queries and scoped workflow/trace
  topology, environment-backed authentication, bounded HTTP reads and shared Python/CLI/agent
  composition. Empty/partial telemetry stays unknown/degraded; no receiver or workflow mutation.
- Add independent connector wire-contract tests, complete YAML example, query API documentation
  and updated schemas. Live consumer qualification and publication remain separate.

- Add evidence-backed deterministic triage with terminal/nonterminal signatures, three-state
  findings, ambiguity/scope sufficiency checks and an optional caller-owned guard.
- Add one opt-in Pydantic AI investigator with native OpenRouter/OpenAI/Anthropic/Gemini,
  dynamic inspect/probe tools, per-run budgets and locally validated candidate/suggestion output.
- Add explicit no-symlink text-file snapshots and fixed read-only Git inspection.
- Add disabled-by-default digest-pinned resource-limited Docker experiments; no network, host
  mounts or host-execution fallback. Probe results are degraded, not independent production proof.
- Add typed incident reports/tool receipts, SQLite incident audit and separate append-only human
  resolution records. No recovery, patch application or automatic learned-rule promotion.
- Add incident/record-resolution/interactive-console CLI, SVG/terminal graph rendering, incident
  API/sandbox documentation, schemas, an executable offline agent notebook and real Docker CI.
- Complete the basic investigation PoC; defer multi-agent orchestration, advanced governance
  and automated recovery until after PoC evaluation. Typed recent-change evidence and live
  provider/consumer evaluation remain open.

- Align operational graph with the design's Pydantic + NetworkX multigraph; expose bounded
  neighborhoods, independent NetworkX exports and dependency-free DOT inspection.
- Share YAML-driven discovery/preparation/investigation across Python, notebooks and CLI;
  enabled source failures produce sanitized incomplete reports and block investigation.
- Add external normalized topology files, explicit identity aliases, Kubernetes resource/service
  links and optional Prometheus service-graph discovery with separate aggregate bounds.
- Add `lumis graph`, `discover --report`, discovered-reference binding, optional YAML replay file,
  runnable offline notebook, graph/API documentation and checkable milestone/readiness roadmap.

- Replace the additive transition with one active architecture: core, graph, connectors,
  reasoning, models, runtime, security and CLI.
- Remove superseded framework APIs, plugin packages, embedded cookbooks, old schemas,
  old phase/release/tutorial documentation and their tests; preserve remote legacy branches.
- Provide independent `lumis init`, `doctor`, configuration-driven `discover` and
  `investigate`, with fresh CLI/YAML/Python/integration documentation.
- Nest project identity, explicit sources, optional model and read-only policy in operational YAML.
- Keep bounded graph/evidence/hypothesis checks and abstention; no remediation executor.
- Default configured models to OpenRouter, with native OpenAI, Anthropic and Gemini adapters;
  shared local validation/redaction/budgets and no hidden retries/fallbacks.
- Replace application-specific CI fixtures with standalone synthetic contracts and clean-wheel smoke.
- Separate SDK milestone gates from live consumer qualification.
