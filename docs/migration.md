# Breaking operational-intelligence reset

The active tree intentionally removes the previous self-healing framework instead of maintaining
two architectures side by side. This is an experimental, pre-1.0 transition.

## Removed from the active SDK

Old `domain`, `application`, `ports`, `adapters`, `config`, `testkit` and evaluation modules;
diagnose/resolve/rules/plugins/memory/config-migrate CLI paths; old configuration/report/action
schemas; PostgreSQL-memory and HTTP-JSON legacy plugin packages; embedded cookbooks;
old phased roadmap, release/tutorial/reference documentation and scenario benchmarks.

Relevant protections survive in the operational kernel: safe bounded document parsing, conservative
redaction, typed observations, graph scoping, bounded/audited investigation and abstention.
There is no compatibility shim implying that old modules still work.

## Preserved history

- [Original implementation](https://github.com/soloshun/lumis-sdk/tree/legacy/pre-operational-intelligence-2026-10-02)
  at `8a371d136946986f19914f1e669744311a4a0825`.
- [Intermediate additive reset](https://github.com/soloshun/lumis-sdk/tree/legacy/additive-reset-2026-10-03)
  at `03bf8738538a722d3fa5ccbdee733afe0d287d9b`.

Use a separate checkout to reproduce an old application or research harness.
Do not combine legacy and operational schemas in one installation.
Legacy history is preserved, not advertised as an actively supported release line.
Published distributions and Git history are not deleted.

## Moving a consumer

1. Identify the SDK commit/version the consumer currently uses.
2. Keep that consumer pinned while creating an independent integration branch.
3. Replace old imports with current contracts and external connector ports.
4. Start a fresh `lumis.yaml` with `lumis init`; do not mechanically rename old rule YAML.
5. Re-express rules as candidate predictions, evidence requests and explicit falsifiers.
6. Normalize incidents/evidence/topology and run withheld-evidence checks.
7. Validate the consumer independently before switching its version pin.

Old memory/report databases are not automatically migrated into the new investigation store.
Keep a separate store file and retain older records under their original schema/version.

## Moving from the candidate baseline to the incident agent

The operational graph/query/evidence contracts remain. Put triage signatures in checks rather
than assuming rule_hypotheses ends an incident. Set terminal/explains_entities only for
multi-observable signatures that genuinely cover the incident; single-condition findings
remain nonterminal. Change the primary call to YamlProject.handle_incident(...) and use the
IncidentReport schema, not the baseline Investigation schema.

Install the agent extra only when using the optional investigator. Review the new
[tool/code/sandbox boundaries](incident-investigation.md), approve explicit file allowlists,
keep probes disabled until a dedicated daemon/image is qualified, and opt in explicitly to
paid calls. Use a separate IncidentStore file/table family; old InvestigationStore records
are not rewritten. Human resolution records are separate from diagnostic truth.

The baseline investigate API is retained for comparisons, not advertised as a tool-agent loop.
