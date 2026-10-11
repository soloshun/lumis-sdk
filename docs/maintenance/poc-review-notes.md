# PoC maintenance review notes

Captured: 10 October 2026 (original review baseline).
Updated: 11 October 2026. Portable implementations and offline verification are ready for review
on `fix/poc-maintenance`; no release or live-provider qualification is claimed.
This backlog covers small, portable SDK improvements using public code and synthetic examples.
It is not a roadmap for turning the proof of concept into an enterprise platform.

## Candidate maintenance work

| ID | Candidate | Status |
|---|---|---|
| SDK-M01 | Distinguish invalid inspection requests from unavailable inspection sources | Ready for review |
| SDK-M02 | Explain receipt digests and truncation clearly | Ready for review |
| SDK-M03 | Preserve failure information when a query is requested again | Ready for review |
| SDK-M04 | Correct the documented CLI evidence-provider list | Ready for review |
| SDK-M05 | Describe `started_at`/`ended_at` as an observation window, not fault onset/recovery | Ready for review |
| SDK-M06 | State what hypothesis validation checks, and what "supported" does not mean | Ready for review |
| SDK-M07 | Warn on predictions and falsifiers that can both pass | Ready for review |
| SDK-M08 | Explain up-front query collection so users can size `max_queries` | Ready for review |
| SDK-M09 | Add a short glossary to the documentation | Ready for review |
| SDK-M10 | Show the model each hypothesis's mechanical state during the run, not only at the end | Offline verified; live pending |
| SDK-M11 | Split the multiplexed `inspect` tool into named tools; put the catalog in the first prompt | Offline verified; live pending |
| SDK-M12 | Keep the prompt prefix stable and enable provider prompt caching | Offline verified; live pending |
| SDK-M13 | A stopping rule for hypotheses (rounds), so the agent reports instead of wandering | Ready for review |
| SDK-M14 | A human-readable report rendering with cited evidence | Ready for review |
| SDK-M15 | Agent instructions: purpose first, a timing rule, room to reason | Offline verified; live pending |
| SDK-M16 | An AWS Bedrock provider option | Offline verified; live pending |
| SDK-M17 | Plain names in outputs and APIs | Ready for review |

### SDK-M01: inspection failure classification

In [InvestigationTools.inspect](../../src/lumis_sdk/investigation/tools.py), the general exception path
returns `denied` with “Inspection denied, unavailable or invalid”. That safely hides exception
details, but conflates malformed requests, authorization denials and unavailable sources for
operations reaching that path.

Proposed small fix: review typed internal errors and stable, redacted reason/status codes. Do
not reveal raw exception messages, URLs or credentials. Check each operation's existing error
handling before changing the public receipt contract.

Verification: synthetic malformed requests, disallowed access and simulated source failures
produce distinguishable safe outcomes; no secret from an exception appears in a receipt.

Implementation and verification (2026-10-11): Safe classification and redaction tests in `test_poc_maintenance.py`.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M02: digest and truncation semantics

[InvestigationTools._receipt](../../src/lumis_sdk/investigation/tools.py) hashes the safe output before
character truncation. Thus `digest` can differ from the hash of the displayed `output`. This
may be intentional; it is not automatically an incorrect hash.

Proposed small fix: document exactly what the digest identifies and expose truncation clearly.
Consider additional metadata only after reviewing schema/API impact. Never imply a hash proves
that the model saw all of the hashed text.

Verification: a long synthetic output exceeds a small budget; assert which bytes are hashed,
which text is returned, and how a caller recognizes incompleteness. Also test an empty remaining
budget and the special handling of validated structural `git.log` output.

Review evidence (2026-10-10): an offline 500-character synthetic receipt with a 100-character
output budget retained the pre-truncation digest and returned truncated text. This confirms
the current semantics; no digest behavior was changed.

Implementation and verification (2026-10-11): Full/visible SHA-256, truncation, zero-budget and structural Git tests.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M03: repeated failed observation queries

[InvestigationTools.collect](../../src/lumis_sdk/investigation/tools.py) records a query in `tried` before
calling the connector. If it times out or fails, asking for that query again returns cached
facts, potentially an empty list with `ok`, without another source read. Avoiding hidden retries
is intentional; hiding the earlier failure behind a success-shaped receipt is worth addressing.

Proposed small fix: retain the attempt outcome and identify cached failure/empty results
accurately. Do not add automatic retries or turn absence into a numeric zero.

Verification: an offline connector times out once; a repeated request does not read it again
and still exposes the failed attempt. Contrast this with a successful query returning no facts.

Review evidence (2026-10-10): a synthetic connector raised an error on its first read. The
second request returned `ok` with `[]`; the connector was called once and no evidence was added.
The timeout variant remains an acceptance scenario for the eventual fix.

Implementation and verification (2026-10-11): Error, timeout and empty-result replay tests; exactly one connector read.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M04: CLI provider documentation

The [Python API extension-port text](../python-api.md#extension-ports) says CLI configuration
accepts only snapshot and Prometheus. The [current validator](../../src/lumis_sdk/runtime/project.py)
also accepts probe, Loki, Tempo, Prefect, SQL and changes, subject to configuration checks.

Proposed small fix: align the text with the actual supported provider/configuration contracts,
linking the relevant configuration and integration guides. This is a documentation correction,
not a request to broaden the allowlist.

Verification: compare the published list with validated configuration examples; explain optional
dependencies and explicit enablement rather than promising every source is enabled by default.

Implementation and verification (2026-10-11): Provider list checked against `OperationalProject`; existing connector/YAML tests retained.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M05: incident window wording

Captured 2026-10-10. [Configuration](../configuration.md) and the
[Python API](../python-api.md) describe `incident.json` with `started_at` and `ended_at`. In
practice, callers (for example the GridCast alert adapter) set `started_at` to the earliest
alert minus a lookback, and `ended_at` to the observation cutoff. These bound the **evidence
window**. They are not when the fault began or when it was resolved. Readers can easily assume
the latter.

Proposed small fix: documentation only. Call the pair the *observation window*. Say that a
lookback is an investigation choice, not a measured onset. Note that every piece of evidence
must fall inside it. Do not rename fields in 0.1.x.

Verification: the docs, README and incident example describe the window consistently.

Implementation and verification (2026-10-11): README, configuration and Python API use observation-window wording; timestamp contract unchanged.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M06: hypothesis validation and "supported"

[`validate_hypothesis_catalog`](../../src/lumis_sdk/core/contracts.py) checks that each
`causal_path` entity exists in the scoped graph and that each check is covered by a registered
query. It does **not** check that consecutive path entities are connected, or connected in the
stated direction. `supported` means every prediction held and no falsifier fired against the
fetched evidence. It is a mechanical result, not proof of causation.

Proposed small fix: documentation first. Add one paragraph to
[incident investigation](../incident-investigation.md) stating both points with a tiny example.
Path-edge validation would be a behavior change, so discuss it separately.

Verification: a synthetic hypothesis whose path skips an edge validates today, as documented.
The wording never presents `supported` as a confirmed cause.

Implementation and verification (2026-10-11): Disconnected synthetic path validates; mechanical support is explicitly unconfirmed.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M07: overlapping prediction and falsifier

A hypothesis may predict `x > 100` and declare the falsifier `x > 0`. Any value above 100 then
both supports and contradicts it, and the evaluator returns `contradicted`. This is correct
mechanically, but almost certainly an authoring mistake by the model or the rule writer.

Proposed small fix: a validation **warning** (not a rejection) when a prediction and a falsifier
on the same entity and key can both be true. Start with numeric comparisons only. Report it in
the receipt or report notes.

Verification: synthetic overlapping and non-overlapping pairs; overlapping ones are flagged.
Assessment results are unchanged.

Implementation and verification (2026-10-11): Numeric overlap boundary tests and unchanged contradicted assessment; warnings are advisory.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M08: up-front query collection

[`handle_incident`](../../src/lumis_sdk/runtime/incident_handler.py) first collects the
de-duplicated union of `initial_queries` and every in-scope rule's `evidence_needed`, then
evaluates the rules. On GridCast this produced 19 reads before any model call, and users may
wonder why. These are code-selected connector reads, not model tool calls, and they count
against `max_queries`.

Proposed small fix: documentation. Describe the order (initial queries, then rule queries,
first occurrence kept), how it consumes the budget, and how to size `max_queries`. Behavior
stays the same.

Verification: an offline project with two rules sharing a query shows one fetch, and the
documented count matches the receipts.

Implementation and verification (2026-10-11): Two rules share one upfront query in the regression; documentation states ordering and budgets.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M09: glossary

New readers meet incident, query, evidence, check, hypothesis, rule, finding, receipt,
assessment and report in one page. A one-table glossary, each term with "what it is" and a
small example, would lower the entry cost. Also define `quality: observed | degraded`, and
"insufficient evidence" versus "requires human expert".

Proposed small fix: add `docs/glossary.md`, link it from the README and the docs index, and keep
it in sync with `core/contracts.py` docstrings.

Verification: every public contract class in `lumis_sdk.core` appears in the glossary.

Implementation and verification (2026-10-11): Regression checks every `lumis_sdk.core.__all__` contract appears in the glossary.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M10: mechanical state during the run

Today the agent registers hypotheses and requests evidence, but candidates are assessed only
after the agent finishes. The model therefore chooses later tests without knowing which
candidates earlier evidence already contradicted or supported.

Proposed fix: after each evidence result, run `assess` for the registered candidates whose
checks use that entity/key, and append a short line to the tool result ("h2: contradicted by
e4; still possible: h1, h3"). The final assessment is unchanged and still authoritative.

Verification: a scripted-model test shows the state line after each evidence call; GridCast
results are re-run and compared (tool calls, tokens, accuracy).

Implementation and verification (2026-10-11): Real scripted Pydantic AI loop sees supported states and citations; ruled-out, unknown and bounded omission tested. GridCast token/tool/accuracy comparison is still pending.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge and the live qualification above


### SDK-M11: named tools instead of one multiplexed tool

`inspect(operation=…)` hides nine operations behind one tool name, and most runs start with a
`catalog` call. Separate tools (`evidence_query`, `graph_neighbourhood`, `changes`, `code_read`,
`git_log`, …) with their own descriptions are easier for models to choose correctly, and the
catalog fits in the first prompt.

Verification: fewer failed tool calls and no catalog round trip in a scripted and a GridCast run.

Implementation and verification (2026-10-11): Named-tool scripted run has three model requests and two tool attempts, without a catalog call. Legacy inspect remains compatible; live tool-error comparison is pending.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge and the live qualification above


### SDK-M12: stable prompt prefix and prompt caching

Agent runs read most input tokens from the provider cache when the prefix is stable (GridCast:
83–90% cached). Keep the instructions, tool definitions and incident bundle unchanged during a
run, and expose the providers' caching settings (e.g. Anthropic `cache_instructions`,
`cache_tool_definitions`).

Verification: cache-read share reported in run metrics.

Implementation and verification (2026-10-11): Mocked Anthropic wire sends cache controls; provider usage and stable initial request are tested. Live cache hit rate, costs and quality remain pending.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge and the live qualification above


### SDK-M13: a stopping rule for hypotheses

Budgets bound tool calls, but nothing says when to stop proposing. A simple rule: an initial
round of up to five candidates, one follow-up round of up to three once the first are
assessed, then test and finish. Refused proposals return the reason to the model.

Verification: a scripted test where the model keeps proposing ends with a report, not a budget
exhaustion.

Implementation and verification (2026-10-11): Broker round-gate tests plus scripted agent refusal ending in a report before request exhaustion.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M14: readable report

`IncidentReport` is precise JSON, but an engineer needs an account: what happened, the
mechanism, the evidence behind each claim, what was ruled out, what remains open, and what
would decide it. A `report.markdown()` renderer built from the assessments and receipts (every
claim cited by evidence or receipt ID) would serve the CLI and the docs.

Verification: snapshot test of the rendering for the playground scenarios.

Implementation and verification (2026-10-11): Four full playground Markdown snapshots in `tests/fixtures/reports`; renderer/CLI escaping tests.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


### SDK-M15: agent instructions

The current instructions are a list of rules. Opening with what the agent is for and what is at
stake (a wrong diagnosis costs more than a slow one), inviting broad thinking about where causes
may sit, and adding a timing rule (a cause starts before its symptoms; older changes in history
are usually not the cause, a GridCast observation) should help without narrowing the model.

Verification: GridCast scenario B (recency) and a no-fault control.

Implementation and verification (2026-10-11): Purpose/timing instructions and a synthetic healthy/no-fault control tested offline; older changes are not excluded solely by age because delayed effects remain possible. Live GridCast recency and no-fault comparison is pending.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge and the live qualification above


### SDK-M16: AWS Bedrock provider

Teams on AWS often want models in their own account. Pydantic AI's Bedrock Converse model makes
this a small provider addition (optional `bedrock` extra), with credentials from the standard
AWS chain, never from configuration files.

Verification: offline construction test; a documented live check.

Implementation and verification (2026-10-11): Pydantic AI Bedrock Converse construction and stubbed wire tests verify model ID, maxTokens, one transport attempt and client closure; live procedure is in models.md. IAM/model qualification is pending.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge and the live qualification above


### SDK-M17: plain names

Some names describe the implementation rather than the meaning. In reports and the CLI,
"contradicted" and "unresolved" read more clearly as "ruled out" and "can't tell" (keeping the
enum values). `handle_incident` could be offered as `investigate`. A finding's `no_match`
could read "did not match (ruled out)". Small renames, aliases for compatibility, and a
glossary entry for each (SDK-M09) would make the outputs readable without the docs.

Verification: CLI output snapshots; old names still accepted.

Implementation and verification (2026-10-11): Plain display labels and four CLI/report snapshots; `investigate_incident` aliases preserve `handle_incident`. Existing baseline `investigate` is not repurposed because it already has a different contract.
See [maintenance verification](verification-2026-10-11.md) for commands and review boundaries.

- [x] Approach reviewed locally (maintainer approval pending)
- [x] Portable fix implemented
- [x] Relevant offline scenarios verified
- [x] API/configuration docs updated if affected
- [ ] Resolved — awaiting reviewed merge


## HTTP/FastAPI question: current support versus a possible recipe

The SDK already reads HTTP through the shipped
[Prometheus, Loki, Tempo and Prefect connectors](../telemetry-connectors.md). The
[offline playground](../notebooks/sdk-playground.ipynb) demonstrates those integrations with
synthetic HTTP responses. An arbitrary application's REST/JSON endpoint has no turnkey generic
provider in the CLI allowlist.

The Python `EvidenceConnector.collect(query, incident)` protocol supports a caller-defined
adapter registered with the runtime. Such an adapter must translate an approved endpoint's
response into bounded, typed `Evidence`; receiving JSON alone does not define evidence semantics.
See the [Python API](../python-api.md#extension-ports) and [integration boundaries](../integrations.md).

An optional FastAPI recipe could demonstrate one fixed read-only endpoint, authentication,
timeouts, schema validation and conversion to evidence with an offline HTTP fixture. This is
a separate proposal, not a minor bug fix or permission for model-chosen arbitrary URLs. Discuss
any change widening network authority under [CONTRIBUTING](../../CONTRIBUTING.md).

## Tracking a fix

For each item, add the following checklist under its record and tick only verified milestones:

```markdown
- [ ] Approach reviewed
- [ ] Portable fix implemented
- [ ] Relevant offline scenarios verified
- [ ] API/configuration docs updated if affected
- [ ] Resolved — link the commit/PR and verification evidence
```

Keep SDK changes independently reviewable. The original capture changed no runtime, schema or
connector behavior; the dated implementation entries above describe the subsequent maintenance.
No item is marked resolved merely because local tests passed.

## Further Pydantic AI integrations

The additional public model/provider integrations under consideration are Groq, Mistral,
Cohere, xAI, Hugging Face and Cerebras. Prefer their Pydantic AI integrations, introduced as
optional extras one provider at a time with credential, timeout, retry, wire/tool and cleanup
contracts. They are not yet selectable in SDK YAML. See [model adoption](../models.md#integration-adoption).
MCP and DBOS require separate tool-authority/workflow designs; they are not part of this batch.
