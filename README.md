# Lumis SDK

Experimental, vendor-neutral **evidence-grounded operational intelligence** for complex systems.
Lumis turns incident context into falsifiable candidate explanations and tests them against
bounded, auditable observations. It is research software, not a production recovery service.

**Evidence first; bounded investigation; human review.** Deterministic signatures run before
one optional tool-using agent. It inspects scoped graph, telemetry and approved code, and can
test hypotheses in an explicitly enabled diagnostic sandbox. Lumis assigns evidence support;
supported does not mean causally proven or confirmed.

## Start here

Read the [documentation entry point](docs/README.md), then follow the
[CLI walkthrough](docs/cli.md) and [YAML reference](docs/configuration.md).
For a complete review order and integration-readiness checklist, start with the
[PoC review guide](docs/review-guide.md).

For this unreleased development architecture, install from the checkout:

```bash
uv sync --all-groups
uv run lumis init --directory /tmp/my-lumis-project
uv run lumis doctor --project /tmp/my-lumis-project/lumis.yaml
uv run lumis discover --project /tmp/my-lumis-project/lumis.yaml
uv run lumis incident --project /tmp/my-lumis-project/lumis.yaml \
  --incident /tmp/my-lumis-project/incident.json \
  --observations /tmp/my-lumis-project/observations.json
```

The scaffold is a small synthetic contract check, not a production scenario or cookbook.
These commands require no consuming project, Kubernetes cluster, HTTP extra or API key.
Expect a nonterminal health finding and human-review report, not an automatic fix.
Use the interactive menu with `uv run lumis console --project /tmp/my-lumis-project/lumis.yaml`.
Export an image with `lumis graph --project ... --format svg --output graph.svg`.

Start with the [incident API guide](docs/incident-investigation.md) and
[agent notebook](docs/notebooks/incident-agent.ipynb). Install optional dependencies with
`uv sync --extra agent`; configure an explicit tool-capable model/credential and opt in with
`lumis incident ... --use-agent`. Configuration alone makes no paid call.

## Implemented boundary

- Validated incident, topology, evidence, candidate and investigation contracts.
- Bounded graph scoping, source validation/deduplication, deterministic evidence checks,
  query/time budgets, normal abstention and SQLite investigation persistence.
- Declared topology, scoped read-only Kubernetes discovery and OTLP JSON export normalization.
- NetworkX directed multigraph, resource/service identity links, bounded graph API and DOT export.
- YAML-led `YamlProject.prepare()` / `investigate()`; per-source discovery reports and automatic
  binding of discovered entity IDs. Optional Prometheus service-graph topology from existing metrics.
- Evidence-backed triage, one bounded Pydantic AI investigator, dynamic inspect/probe tools,
  scoped allowlisted code/Git, redacted receipts and tentative suggestions.
- Opt-in resource-limited Docker experiments; never host execution or production-fix verification.
- JSON/DOT/SVG/terminal graph exports, interactive CLI, SQLite incident audit and manual resolutions.
- Optional Prometheus observations and opt-in model candidates/agents: OpenRouter (default),
  native OpenAI, Anthropic and Gemini. See [model configuration](docs/models.md).

No remediation executor, automatic learned-rule promotion, live OTLP receiver, hosted service,
or complete autonomous operational lifecycle is shipped.
See [architecture](docs/architecture.md), [Python API](docs/python-api.md) and [roadmap](ROADMAP.md).
For hands-on local testing, use the [offline notebook](docs/notebooks/operational-graph.ipynb).
Review [sandbox limitations](docs/sandbox.md) before enabling generated experiments.

## Independent framework, external applications

Applications connect through standard telemetry, exported topology and observation contracts.
The SDK never imports GridCast or another application. Application examples live in the separate
Lumis cookbooks project; they are not SDK development prerequisites.
See [integration boundaries](docs/integrations.md).

## Development and history

Changes branch from `dev` and return by reviewed PR. `main` promotion and package publication
are separate release steps; this cleanup does not publish a package.
The metadata currently remains `0.1.0rc1`; the target final pre-1.0 release is `0.1.0`.
It must not be presented as an already published version of this new architecture.

Superseded APIs, cookbooks and documentation are absent from the active tree and preserved on
[legacy/pre-operational-intelligence-2026-10-02](https://github.com/soloshun/lumis-sdk/tree/legacy/pre-operational-intelligence-2026-10-02).
The intermediate additive reset is preserved on
[legacy/additive-reset-2026-10-03](https://github.com/soloshun/lumis-sdk/tree/legacy/additive-reset-2026-10-03).
See [migration](docs/migration.md), [contributing](CONTRIBUTING.md) and [release runbook](docs/releasing.md).
