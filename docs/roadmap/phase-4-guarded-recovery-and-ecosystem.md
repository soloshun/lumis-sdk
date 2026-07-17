# Phase 4 — Guarded recovery and ecosystem maturity

Sprints: 18–23

## Phase outcome

Lumis SDK defines portable, independently implemented protocols for authorized recovery and
verification while retaining no default production executor. The ecosystem has mature capability
negotiation, signing, policy conformance, migrations, cross-language artifacts, education, and
governance suitable for a `2.0` compatibility decision.

## Entry criteria

- Phase 3 provides measured incident/evidence context and independent adopters.
- An RFC and threat model approve any new side-effecting capability.
- At least two execution-boundary implementers agree on the protocol before it is declared stable.

## Sprint 18 — Side-effect-aware plugin capabilities

**Outcome:** plugins declare capability, authority, side effects, trust level, lifecycle, and
conformance requirements precisely enough for hosts to fail closed before loading.

- [ ] Evaluate stable capabilities for policy evaluator, action executor, recovery verifier,
      redactor, correlation provider, lineage provider, model-profile provider, and notification
      channel.
- [ ] Add read-only/mutating, reversible/irreversible, local/network, secret, model, and human-
      decision metadata.
- [ ] Add required/optional capability negotiation and machine-readable denial reasons.
- [ ] Add lifecycle, health, support, provenance, isolation, and deprecation contracts.
- [ ] Expand testkit fixtures for hostile manifests, authority escalation, and partial capability.

**Acceptance evidence:** discovering/installing a plugin grants no authority; incompatible or
under-declared side effects are rejected before runtime construction.

## Sprint 19 — Executor and independent verifier protocols

**Outcome:** approved hosts can compose an external executor and independent verifier through
versioned, idempotent, dry-run-first contracts without core owning credentials or scheduling.

- [ ] Define action parameters/results, preconditions, authorization reference, idempotency,
      attempt, timeout, compensation, and sanitized failure contracts.
- [ ] Define dry-run/shadow behavior and require an explicit transition to side-effecting mode.
- [ ] Separate executor result from recovery verification; executor success is never recovery.
- [ ] Define verifier requests/results, evidence references, timing windows, independence metadata,
      and failed/unknown escalation.
- [ ] Add reusable conformance tests and only reversible synthetic/local sandbox executors.
- [ ] Keep shell, arbitrary SQL, unrestricted HTTP, and ambient cloud credentials out of core.

**Acceptance evidence:** duplicate requests are safe, missing/expired authorization fails closed,
and failed/unknown verification cannot create confirmed memory.

## Sprint 20 — Signed envelopes, replay defense, and policy conformance

**Outcome:** control planes and runners can exchange canonical, time-bounded, replay-resistant
decisions and prove equivalent policy behavior without choosing one transport or KMS.

- [ ] Define canonical envelope hash, algorithm/key metadata, timestamp, nonce, expiry,
      idempotency key, signer/audience, and replay decision contracts.
- [ ] Publish deterministic test vectors and clock-skew/rotation/replay fixtures.
- [ ] Define stable policy input, decision, matched rules, constraints, reasons, and artifact hashes.
- [ ] Add conformance fixtures proving equivalent decisions across host and runner.
- [ ] Evaluate OPA/Rego and signed policy bundles as optional adapters, not mandatory core.
- [ ] Add Slack/Teams notification packages only as non-authoritative decision transports.

**Acceptance evidence:** test vectors interoperate across at least two implementations; a channel
message alone cannot become authoritative approval.

## Sprint 21 — Configuration migration, doctor, and compatibility maturity

**Outcome:** projects and plugins can evolve through machine-readable migrations and deprecations
without silent behavior changes or secret disclosure.

- [ ] Add chained, idempotent configuration migrations with dry-run diff and backup guidance.
- [ ] Extend doctor checks for model profiles/routes, prompt packages, plugin capabilities,
      signatures, policies, and compatibility.
- [ ] Define SDK/plugin protocol versions, capability requirements, min/max compatibility,
      deprecation notices, replacement paths, and negotiation failures.
- [ ] Publish compatibility matrices and automate old-project/plugin fixtures in CI.
- [ ] Ensure diagnostics redact credential values and untrusted evidence.

**Acceptance evidence:** every supported old fixture migrates deterministically or fails with an
actionable reason; doctor output contains no secret material.

## Sprint 22 — Language-neutral protocol and TypeScript decision

**Outcome:** non-Python applications can validate/exchange stable documents and run conformance
fixtures before the project commits to a second runtime implementation.

- [ ] Inventory language-neutral domain/config/plugin/policy/verification schemas and canonical
      serialization/hash rules.
- [ ] Publish a versioned protocol bundle with JSON Schema, examples, test vectors, and semantic
      compatibility rules.
- [ ] Generate TypeScript types and validators as a proof; test round trips against Python.
- [ ] Evaluate native TypeScript SDK demand, maintenance capacity, async/runtime differences,
      packaging, security, and release ownership in an RFC.
- [ ] If approved, begin with document validation and client-side composition—not a duplicated
      executor or provider ecosystem.
- [ ] Keep Java/Go/Rust bindings in the same evidence-gated queue rather than promising parity.

**Acceptance evidence:** Python and generated TypeScript artifacts agree on canonical fixtures;
the RFC records a clear build/defer decision and ownership model.

## Sprint 23 — Education, community, and `2.0` readiness

**Outcome:** users can discover, learn, extend, and maintain the framework through durable written
and video material, examples, governance, and compatibility evidence.

- [ ] Launch the documentation site from versioned repository sources with API, concepts,
      cookbook, plugin, migration, security, and release sections.
- [ ] Publish phase overview videos and reproducible tutorials for local diagnosis, Prometheus,
      AWS evidence, custom PostgreSQL memory, model routing, lineage, and guarded sandbox recovery.
- [ ] Add project templates, example gallery, integration catalog, contributor mentorship path,
      RFC index, and good-first-issue curation.
- [ ] Establish release cadence, support windows, deprecation calendar, maintainer succession,
      package ownership, and archived-plugin process.
- [ ] Run ecosystem compatibility, security, performance, documentation, and independent-adopter
      qualification before deciding `2.0` scope.
- [ ] Publish an honest maturity report and defer unresolved authority or ownership risks.

**Acceptance evidence:** tutorials are pinned to tested revisions and have written equivalents;
multiple independent plugins/applications pass the protocol suite; `2.0` has a public go/no-go
decision rather than a date-only promise.

## Phase 4 exit criteria

- Core still has no default production executor and no ambient provider authority.
- Execution, verification, signing, replay, and policy protocols have independent implementations.
- Compatibility and migrations are machine-readable and exercised against historical fixtures.
- Language-neutral artifacts interoperate; any native TypeScript SDK has explicit ownership.
- Documentation, examples, videos, governance, and support processes are sustainable.
