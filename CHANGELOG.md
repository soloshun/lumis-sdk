# Changelog

## Unreleased — standalone operational-intelligence reset

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
- Separate SDK milestone gates from live consumer qualification. No new index release is claimed.
