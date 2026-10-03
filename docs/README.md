# Documentation: start here

This is the active standalone operational-intelligence SDK documentation. Historical documentation
lives on the legacy branches, not alongside the current API.

## Reading order

1. [Architecture](architecture.md): what the SDK does, package boundaries and safety model.
2. [CLI walkthrough](cli.md): install from source, initialize, inspect, discover and investigate.
3. [YAML reference](configuration.md): every supported project field and a complete configuration.
4. [Python API](python-api.md): compose the same runtime independently of the CLI.
   Start with the [offline notebook](notebooks/operational-graph.ipynb) and [graph/lineage guide](graph.md)
   to inspect NetworkX topology and test YAML-led investigation.
5. [Model providers](models.md): OpenRouter default, native OpenAI/Anthropic/Gemini wrappers.
6. [Integration boundaries](integrations.md): connect any application through external data.
7. [Migration](migration.md): breaking reset and how to retrieve the previous implementation.
8. [Verification](verification.md): local checks, offline contracts and release evidence.
9. [Release runbook](releasing.md): maintainers' dev → main → release procedure.

The [roadmap](../ROADMAP.md) separates implemented SDK work from future capability and external
consumer validation. Contributors should also read [CONTRIBUTING.md](../CONTRIBUTING.md).

Documentation-site authors can use these files directly as source content. Each sprint must
update API, CLI/configuration, limitations, tests and release notes together.
