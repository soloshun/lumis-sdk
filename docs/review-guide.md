# PoC review: start here

## Where the SDK is now

The incident-investigation PoC is implemented on dev. The implementation entered through
[PR #101](https://github.com/soloshun/lumis-sdk/pull/101):
incident → scoped graph/context → evidence-backed deterministic triage → one optional
tool-using investigator → isolated diagnostic experiments → mechanically assessed report →
human review and optional manual resolution record.

It stops at reporting/proposals. It does not apply patches, recover services or promote rules.
Further orchestration, learning and policy-controlled execution are not implemented yet and
are deferred until after PoC evaluation.

Implementation verification included 157 passing tests with real Docker probes; the Python
3.12/3.13 offline suites passed 150 tests with seven explicit Docker opt-in skips each.
All eight PR checks passed. These verify contracts and isolation, not live model accuracy.

The experimental release of this architecture is `lumis-sdk==0.1.0`. The older `0.1.0rc1`
upload belongs to the previous architecture; do not test these docs against it.

## Review order

1. [README](../README.md): package purpose, implemented surface and install boundary.
2. [Incident investigation](incident-investigation.md): primary API, triage, tools,
   configuration, report semantics and manual resolution storage.
3. [Agent notebook](notebooks/incident-agent.ipynb): execute the offline walkthrough.
   Expected: a nonterminal finding first routes to human; the scripted real agent loop then
   reads approved code and produces an unconfirmed human-review report. No paid model or Docker.
4. [Graph notebook](notebooks/operational-graph.ipynb) and [graph guide](graph.md):
   inspect NetworkX topology, identities, direction and bounded graph scope.
5. [CLI](cli.md), [YAML](configuration.md) and [Python API](python-api.md):
   review the entry points you will use in your integration.
6. [Sandbox](sandbox.md) and [model configuration](models.md):
   approve code/image/provider access before enabling real probes or paid calls.
7. [Integration matrix](integrations.md), [roadmap](../ROADMAP.md) and
   [verification](verification.md): distinguish implemented capability from qualification
   and future work.

Use handle_incident / lumis incident for the new PoC. investigate / --use-model remains the
single-completion candidate baseline, not the tool-agent workflow.

## Code entry points

| Review | File |
| --- | --- |
| Public Python composition: from_file, prepare, handle_incident | [runtime/session.py](../src/lumis_sdk/runtime/session.py) |
| YAML fields and graph/query reference validation | [runtime/project.py](../src/lumis_sdk/runtime/project.py) |
| End-to-end incident routing and report assembly | [runtime/incident_handler.py](../src/lumis_sdk/runtime/incident_handler.py) |
| Deterministic findings/sufficiency and caller guard | [checks/engine.py](../src/lumis_sdk/checks/engine.py) |
| Typed findings, agent output, receipts, reports and resolutions | [investigation/contracts.py](../src/lumis_sdk/investigation/contracts.py) |
| One Pydantic AI investigator and two tool families | [investigation/agent.py](../src/lumis_sdk/investigation/agent.py) |
| Scoped tool catalog, attempts, observations and probe binding | [investigation/tools.py](../src/lumis_sdk/investigation/tools.py) |
| Native provider construction | [investigation/providers.py](../src/lumis_sdk/investigation/providers.py) |
| Allowlisted source snapshots/read-only Git | [connectors/code.py](../src/lumis_sdk/connectors/code.py) |
| Generated-code isolation and cleanup | [sandbox/runner.py](../src/lumis_sdk/sandbox/runner.py) |
| Mechanical hypothesis support/contradiction | [reasoning/evaluator.py](../src/lumis_sdk/reasoning/evaluator.py) |
| Immutable audit and separate human attestations | [runtime/incident_store.py](../src/lumis_sdk/runtime/incident_store.py) |
| CLI registration and incident/menu commands | [cli/app.py](../src/lumis_sdk/cli/app.py), [cli/incident.py](../src/lumis_sdk/cli/incident.py) |

For implementation evidence, start with [incident tests](../tests/test_incident_agent.py),
[isolation tests](../tests/test_investigation_safety.py) and
[notebook tests](../tests/test_documented_notebook.py).

## A first local review

Run from the SDK checkout:

    uv run lumis --help
    uv run lumis init --directory /tmp/lumis-poc-review
    uv run lumis doctor --project /tmp/lumis-poc-review/lumis.yaml
    uv run lumis graph --project /tmp/lumis-poc-review/lumis.yaml --format terminal
    uv run lumis graph --project /tmp/lumis-poc-review/lumis.yaml --format svg --output /tmp/lumis-poc-review/graph.svg
    uv run lumis incident --project /tmp/lumis-poc-review/lumis.yaml --incident /tmp/lumis-poc-review/incident.json --observations /tmp/lumis-poc-review/observations.json
    uv run lumis console --project /tmp/lumis-poc-review/lumis.yaml

Choose an unused directory/file for repeated scaffold/export runs. Expected report: health
finding match, route human, requires_human_expert, unconfirmed_hypothesis and human review true.
This is deliberate: the scaffold signature is nonterminal and no agent is implicitly enabled.
Then run the agent notebook for the actual tool-loop walkthrough.

## Is it enough to start GridCast testing?

**Yes for a bounded first integration test; not yet a qualified all-scenario integration.**
The SDK does not need future learning, multi-agent orchestration or automatic recovery to start.
The cookbook still needs a current configuration and an external test/evaluation harness.
Its existing integration draft has earlier API/schema assumptions and planned adapters.
Do not copy its YAML unchanged.

First-test checklist:

- [ ] Pin the intended SDK dev commit and record environment/dependency versions.
- [ ] Choose one controlled scenario with discriminating evidence available through supported
  observations; inspect coverage before claiming a diagnosis is possible.
- [ ] Map actual canonical graph IDs, source scope, service labels and incident time window.
- [ ] Register approved Prometheus/Loki/Tempo/Prefect queries or external normalized observations.
- [ ] Configure evidence-backed checks and exact code/Git file allowlists.
- [ ] Qualify the dedicated sandbox and an explicit tool-capable model before enabling either.
- [ ] Run healthy, known-signature, uncertain, missing-data and conflicting-evidence cases.
- [ ] Save findings, hypotheses, receipts, probe results, abstentions and usage measurements.
- [ ] Keep hidden fault labels outside Lumis; score against them only after the report.
- [ ] Apply any fix manually, verify it externally and separately record the human resolution.

No controlled GridCast fault-scenario or paid-provider quality evaluation was performed.
Limited live read-only connector transport checks are recorded in [verification](verification.md).
Prometheus, Loki, Tempo and Prefect observations and basic code/Git tools are supported.
Use the [connector setup guide](telemetry-connectors.md) before live testing. SQL evidence,
OpenLineage ingestion and typed recent-change queries are not implemented yet. Scenarios requiring
those need reviewed external normalization or adapter work; a model cannot replace absent evidence.

## What remains

For the current PoC: first cookbook wiring, live provider/tool/schema/privacy/cost qualification,
controlled scenario evaluation and any independently reproduced fixes found by those tests.
Track consumer qualification in #96, typed change evidence in #99, independent review in #57
and experimental publication in #9.

After PoC evaluation: broader adapters, measured query-selection improvements, reusable memory,
reviewed rule promotion and advanced proposal/verification workflows. These are roadmap work,
not prerequisites for the first bounded integration test. Automatic recovery remains unavailable.
