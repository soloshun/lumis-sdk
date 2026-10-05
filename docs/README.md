# Documentation: start here

This is the active standalone operational-intelligence SDK documentation. Historical documentation
lives on the legacy branches, not alongside the current API.

## Reading order

New to Lumis? Start with [using Lumis on a small project](small-project.md): one service,
Prometheus and one deterministic check, with a tested example.

For one explained offline walkthrough, start with the [synthetic SDK playground](notebooks/sdk-playground.ipynb)
and its [kernel/setup guide](notebooks/README.md). It combines graphs, all four HTTP connectors,
deterministic/agent routes, a separate scripted text stream, safety checks and audit records.

For a maintainer review, begin with [PoC review guide](review-guide.md): current status,
ordered documentation/code entry points, expected local outputs and the first GridCast test gate.

1. [Architecture](architecture.md): what the SDK does, package boundaries and safety model.
   Then [incident investigation](incident-investigation.md) for the recommended deterministic →
   agent → human-review flow and [sandbox threat model](sandbox.md) before enabling experiments.
   Try the new [agent notebook](notebooks/incident-agent.ipynb) offline.
2. [CLI walkthrough](cli.md): install from source, initialize, inspect, discover and investigate.
3. [YAML reference](configuration.md): every supported project field and a complete configuration.
4. [Python API](python-api.md): compose the same runtime independently of the CLI.
   Start with the [offline notebook](notebooks/operational-graph.ipynb) and [graph/lineage guide](graph.md)
   to inspect NetworkX topology and test YAML-led investigation.
5. [Model providers](models.md): OpenRouter default, native OpenAI/Anthropic/Gemini wrappers.
6. [Integration boundaries](integrations.md): connect any application through external data.
   Follow [Loki/Tempo/Prefect setup](telemetry-connectors.md) for real read-only endpoints and
   registered observation queries; begin from the [complete example](examples/telemetry-project.yaml).
7. [Migration](migration.md): breaking reset and how to retrieve the previous implementation.
8. [Verification](verification.md): local checks, offline contracts and release evidence.
9. [Release runbook](releasing.md): maintainers' dev → main → release procedure.

The [roadmap](../ROADMAP.md) separates implemented SDK work from future capability and external
consumer validation. Contributors should also read [CONTRIBUTING.md](../CONTRIBUTING.md).

Documentation-site authors can use these files directly as source content. Each sprint must
update API, CLI/configuration, limitations, tests and release notes together.
