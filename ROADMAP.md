# Lumis SDK phased roadmap

Date: 2026-07-17

Lumis SDK is an Apache-2.0, vendor-agnostic Python framework for building evidence-grounded,
guarded incident-response and pipeline-recovery systems. The roadmap develops reusable contracts,
reference adapters, optional packages, test utilities, and relatable examples without turning the
SDK into the hosted Lumis product or granting ambient production authority.

## Roadmap documents

1. [`docs/roadmap/phase-1-trustworthy-python-foundation.md`](docs/roadmap/phase-1-trustworthy-python-foundation.md)
   covers Sprints 0–6: the delivered deterministic foundation and the final stable-contract,
   security, documentation, adoption, and `0.1.0` readiness sprint.
2. [`docs/roadmap/phase-2-model-prompt-and-bounded-agents.md`](docs/roadmap/phase-2-model-prompt-and-bounded-agents.md)
   covers Sprints 7–11: provider-neutral model routing, prompt packages, evidence planning,
   read-only tools, loop guards, grounding, and evaluation gates.
3. [`docs/roadmap/phase-3-intelligence-memory-and-integrations.md`](docs/roadmap/phase-3-intelligence-memory-and-integrations.md)
   covers Sprints 12–17: correlation, lineage, rule analytics, memory quality, semantic retrieval,
   and demand-led observability, data, orchestration, cloud, and delivery integrations.
4. [`docs/roadmap/phase-4-guarded-recovery-and-ecosystem.md`](docs/roadmap/phase-4-guarded-recovery-and-ecosystem.md)
   covers Sprints 18–23: side-effect-aware plugin contracts, executor/verifier protocols, signing,
   policy conformance, migrations, cross-language schemas, education, and ecosystem maturity.

An internal backend-authored candidate review was used as design input. The public
[`candidate mapping`](docs/roadmap/candidate-capability-mapping.md) records how each generally
useful proposal was independently classified and sequenced without exposing or depending on
private product documentation.

## Phase model

| Phase | Sprints | Outcome | Exit condition |
| --- | --- | --- | --- |
| Phase 1 — trustworthy Python foundation | 0–6 | Stable, secure, documented Python contracts and independently usable reference paths | Phase 1 gates met; external evidence recorded; pre-1.0 `0.1.0` release approved |
| Phase 2 — model, prompt, and bounded agents | 7–11 | Replayable provider-neutral reasoning and read-only evidence planning with hard budgets | Multiple adapters pass offline conformance; evaluation gates prevent unsafe promotion |
| Phase 3 — intelligence, memory, and integrations | 12–17 | Explainable cross-system context, quality-aware memory, and useful optional integration packages | Measured standalone value across several domains without mandatory vendor dependencies |
| Phase 4 — guarded recovery and ecosystem | 18–23 | Portable recovery protocols and a mature multi-language-friendly ecosystem with no default executor | Protocol/security review, multiple independent implementations, and documented `2.0` decision |

Phase numbers describe capability maturity. They do not imply separate services, a hosted account,
or a commitment to implement every named integration in core.

## Working agreement

- Core remains deterministic-first, local-first, model-optional, vendor-neutral, and useful with
  no plugins installed.
- A provider, framework, protocol, database extension, cloud, or heavy dependency belongs in an
  optional package behind a stable port.
- SaaS tenancy, hosted secrets, billing, entitlements, UI ownership, managed infrastructure,
  enterprise administration, and commercial operations remain in Lumis—not the SDK.
- Models may classify, rank, plan evidence, and suggest allowlisted playbooks. They may not verify
  recovery, manufacture confirmed truth, create arbitrary commands, or grant execution authority.
- Recovery protocols remain allowlisted, policy-bound, attributable, idempotent, bounded,
  reversible where possible, independently verified, and fail-closed.
- Every behavior-changing sprint updates API/reference documentation, schemas where applicable,
  at least one runnable example, changelog/upgrade notes, and the documentation-site source queue.
- Tutorial video work is tracked as a release deliverable: each phase gets an overview and each
  major adoption path gets a reproducible script, repository revision, and written equivalent.
- TypeScript begins with language-neutral JSON Schema and conformance fixtures. A native runtime
  starts only after an RFC proves value beyond generated types and avoids semantic drift.

## Definition of done

A sprint is complete only when:

1. public contracts and safety invariants are explicit;
2. implementation is vendor-neutral or isolated in an optional package;
3. deterministic unit, contract, integration, hostile-input, and replay tests pass as relevant;
4. compatibility, migration, authority, and failure behavior are documented;
5. runnable synthetic/public examples demonstrate the capability without paid keys in CI;
6. checked schemas and testkit fixtures are current;
7. security review, dependency audit, SAST, distributions, and clean installs pass;
8. API docs, cookbook docs, changelog, roadmap status, and video script queue are updated;
9. GitHub issues and project items link the accepted implementation evidence; and
10. implemented behavior is not overstated as autonomous recovery or production efficacy.

## Issue promotion workflow

1. Keep future phases documentation-only until the maintainer approves the phase.
2. Re-check the latest SDK and plugin releases before accepting a candidate.
3. Validate every candidate against one standalone or second-product use case.
4. Classify it as core, official optional package, community package, example, or product-only.
5. Approve one sprint at a time and create only that sprint's implementation issues/project items.
6. Branch from `dev`, implement and document, merge through a reviewed PR to `dev`, then qualify a
   separate `dev` → `main` release.
7. Publish core and optional packages independently through trusted publishing and verify public
   clean installation before closing release issues.

## Current status

| Sprint | Status | Released outcome | Tracking |
| --- | --- | --- | --- |
| 0 — maintainer baseline | Complete | Structured deterministic rules and open-source CI (`0.0.2`) | #1 |
| 1 — evidence and reporting | Complete | Bounded evidence, JSON reports, doctor checks, stable testkit (`0.0.3`/`0.0.4`) | #4, #19 |
| 2 — plugin SDK | Complete | Governed discovery, manifests, compatibility and authority checks (`0.0.6`) | #5 |
| 3 — durable memory and connectors | Complete | PostgreSQL memory, webhook normalization, HTTP JSON evidence (`0.0.7`) | #2, #6 |
| 4 — policy and playbook proposals | Complete | Evidence-linked, approval-aware, non-executing proposals (`0.0.8`) | #7, #47, #48 |
| 5 — verification and learning | Complete | Explicit verification truth, transparent retrieval, replay evaluation (`0.0.8`) | #8, #49, #50 |
| 6 — trustworthy Python foundation | In progress | Stable contracts, security/release hardening, adoption evidence, and `0.1.0` qualification | #9 |

Earlier roadmap labels such as `v0.4` and `v0.5` identify capability milestones, not Python
package versions. Sprint 6 is explicitly targeted to package release `0.1.0`; a future decision
after Sprint 7 may consider the path toward `1.0.0`.
