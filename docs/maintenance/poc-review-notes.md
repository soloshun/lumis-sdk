# PoC maintenance review notes

Captured: 10 October 2026. **Notes only; no fixes implemented by this review.**
This backlog covers small, portable SDK improvements using public code and synthetic examples.
It is not a roadmap for turning the proof of concept into an enterprise platform.

## Candidate maintenance work

| ID | Candidate | Status |
|---|---|---|
| SDK-M01 | Distinguish invalid inspection requests from unavailable inspection sources | Open |
| SDK-M02 | Explain receipt digests and truncation clearly | Open |
| SDK-M03 | Preserve failure information when a query is requested again | Open |
| SDK-M04 | Correct the documented CLI evidence-provider list | Open |

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

### SDK-M04: CLI provider documentation

The [Python API extension-port text](../python-api.md#extension-ports) says CLI configuration
accepts only snapshot and Prometheus. The [current validator](../../src/lumis_sdk/runtime/project.py)
also accepts probe, Loki, Tempo, Prefect, SQL and changes, subject to configuration checks.

Proposed small fix: align the text with the actual supported provider/configuration contracts,
linking the relevant configuration and integration guides. This is a documentation correction,
not a request to broaden the allowlist.

Verification: compare the published list with validated configuration examples; explain optional
dependencies and explicit enablement rather than promising every source is enabled by default.

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

Keep SDK changes independently reviewable. No runtime, schema or connector behavior was changed
when these notes were captured.
