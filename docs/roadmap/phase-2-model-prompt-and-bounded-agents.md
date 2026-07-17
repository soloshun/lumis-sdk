# Phase 2 — Model, prompt, and bounded-agent contracts

Sprints: 7–11

## Phase outcome

Applications can compose provider-neutral model profiles, versioned prompts, typed evidence plans,
read-only tools, hard loop budgets, grounding validation, and evaluation promotion gates. Core
still works without a model and no agent framework type enters public domain contracts.

## Entry criteria

- Phase 1 stable-surface and migration decisions are published.
- At least two prospective adapters or applications validate the model/profile vocabulary.
- The maintainer approves RFC scope for candidate capabilities 1–17.

## Sprint 7 — Model stages, profiles, credentials, policy, and routing

**Outcome:** a deterministic router turns task requirements plus policy into an explained ordered
attempt plan without making a network call.

- [ ] Define extensible `ModelTask` and non-generative verification/execution exclusions.
- [ ] Define provider connection, model identity/revision, profile, stage route, and fallback
      contracts for direct, aggregator, local, and test-double modes.
- [ ] Add capability declarations and deterministic negotiation for schema output, tools, context,
      modality, streaming, usage, reasoning controls, and data location.
- [ ] Introduce redaction-safe `CredentialRef` values for environment, vault, managed, and
      runner-local ownership; never serialize secret values.
- [ ] Extend model-use policy with independently bounded tokens, cost, time, retries, concurrency,
      tool calls, evidence bytes, fallback count, and duplicate-request behavior.
- [ ] Produce an explained attempt plan and normalized no-provider/fail-closed outcomes.
- [ ] Expand invocation events with route/profile/policy hashes, attempts, capability snapshot,
      usage, cost, latency, finish reason, and sanitized errors.
- [ ] Add fake profile providers, negotiation fixtures, JSON Schemas, API docs, and routing replay.

**Acceptance evidence:** offline route matrix across direct/aggregator/local profiles; every
rejection is explained; credentials and provider SDK types never enter serialized core records.

## Sprint 8 — Versioned prompt packages and safe rendering

**Outcome:** prompt changes are immutable, reviewable, reproducible, and separated from untrusted
evidence.

- [ ] Define prompt identity, purpose, stage, revision, lifecycle, provenance, evaluation
      reference, expected schema reference, and canonical content hashes.
- [ ] Separate locked safety/policy instructions, managed task text, optional user overlay, and
      untrusted evidence sections.
- [ ] Add draft, publish, supersede, rollback, and semantic diff contracts.
- [ ] Add deterministic typed rendering with required-variable checks, escaping, section
      boundaries, output-size limits, and secret-interpolation rejection.
- [ ] Keep prompt content project-owned; ship synthetic presets only as examples.
- [ ] Add tamper, injection, Unicode, missing-variable, oversize, and rollback tests.
- [ ] Publish prompt-author and adapter guides plus a provider-independent cookbook.

**Acceptance evidence:** canonical render fixtures are identical across supported Python versions;
untrusted evidence cannot alter the locked instruction section or expand tools/authority.

## Sprint 9 — Triage state machine, evidence plans, and read-only tools

**Outcome:** an application can inspect and replay how an incident moved from intake through
deterministic matching, bounded evidence planning, diagnosis, confidence gating, and escalation.

- [ ] Add typed states, events, transition validator, terminal reasons, and idempotency identity.
- [ ] Define evidence objectives, expected signal, hypothesis relationship, sensitivity, bounds,
      deduplication key, observations, and collection outcome.
- [ ] Define tool descriptors with typed input/output schema, side-effect class, data class,
      timeout, cost, and authority metadata.
- [ ] Permit only read-only evidence tools in diagnostic plans; mutating tools fail validation.
- [ ] Keep orchestration/persistence outside the pure transition core.
- [ ] Add framework-neutral conformance fixtures and adapters for existing evidence providers.
- [ ] Add an offline multi-step investigation cookbook and state-transition visualization source.

**Acceptance evidence:** deterministic replay reaches the same state and evidence plan; unknown or
mutating capabilities escalate without a model call or side effect.

## Sprint 10 — Agent budgets, grounding, and conformance testkit

**Outcome:** every bounded-agent adapter inherits the same exhaustion, citation, redaction, and
audit semantics.

- [ ] Add reusable guards for steps, elapsed time, tool calls, per-tool calls, evidence volume,
      tokens, cost, fallback attempts, duplicate calls, and repeated requests.
- [ ] Define exhausted, denied, failed, and escalated outcomes without false success.
- [ ] Validate facts/hypotheses against accessible evidence IDs and report citation coverage,
      unsupported claims, missing evidence, and explicit uncertainty.
- [ ] Add fake/function models, invalid/truncated output, timeout/rate-limit, capability mismatch,
      and deterministic tool fixtures.
- [ ] Add reusable assertions for budgets, citations, redaction, invocation audit, and refusal of
      mutating tools.
- [ ] Prove adapters for at least two agent-runtime shapes without leaking their types into core.

**Acceptance evidence:** hostile and repeated-request fixtures terminate within declared bounds;
unsupported claims cannot be promoted to confirmed facts or recovery authority.

## Sprint 11 — Evaluation datasets and promotion policies

**Outcome:** prompts, models, routes, tools, and budgets change only through transparent offline
quality/safety evidence.

- [ ] Define versioned license-aware incident cases, fixture provenance, expected outcomes, and
      dataset splits without private/customer data.
- [ ] Add composable evaluators for schema validity, citation coverage, unsupported claims,
      missing evidence, unsafe-action refusal, ranking, latency, tokens, cost, and tool use.
- [ ] Add repeated-run distributions while preserving deterministic exact evaluators.
- [ ] Define baseline/candidate comparisons, thresholds, regressions, waivers, and promotion
      decisions for prompts, models, routes, tools, and budgets.
- [ ] Add CI-ready reports and machine-readable results without prescribing a hosted evaluator.
- [ ] Publish benchmark methodology, limitations, and a video/tutorial script.

**Acceptance evidence:** a deliberately unsafe or regressed candidate is rejected in CI with
inspectable reasons; no benchmark is presented as universal production performance.

## Phase 2 exit criteria

- Model/provider/runtime choices are replaceable behind stable contracts.
- Prompts and routing are hash-pinned, bounded, observable, and evaluation-gated.
- Evidence planning and tools are typed, read-only, and replayable.
- At least two independent adapter shapes pass the same offline conformance kit.
- Deterministic-only users incur no model/runtime dependency.
