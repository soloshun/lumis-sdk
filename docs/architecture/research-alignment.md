# Research alignment and experimental status

## Status

Lumis SDK is an **experimental, work-in-progress implementation companion** to the paper
[_Agentic Self-Healing for Data & AI Pipelines: An Affordable Vendor-Agnostic Architecture using
Open-Source Software_](https://arxiv.org/abs/2608.01955)
([arXiv:2608.01955](https://doi.org/10.48550/arXiv.2608.01955)). The repository is public so
researchers, practitioners, students, and open-source contributors can inspect the architecture,
reproduce bounded examples, report limitations, and help evaluate the design.

The paper proposes a reference architecture; it does not claim an empirically validated,
production-ready autonomous recovery product. Likewise, the SDK's current contracts and reference
adapters are not a production remediation service. Interfaces and behavior may change before
broader production-readiness claims are considered.

## Paper-to-SDK boundary

The paper defines seven logical layers and an eight-stage lifecycle. The SDK implements reusable,
vendor-neutral parts of that design incrementally rather than requiring the paper's illustrative
tool stack.

| Paper responsibility | SDK direction and present boundary |
| --- | --- |
| Existing pipeline estate | Remains adopter-owned; the SDK does not replace an orchestrator, warehouse, model platform, or CI/CD system. |
| Telemetry and signals | Bounded evidence/provider contracts and optional adapters; no mandatory observability vendor. |
| Incident memory and accumulated knowledge | Local SQLite plus an optional PostgreSQL plugin, explicit truth state, and explained retrieval. |
| Deterministic policy and agentic reasoning | Deterministic rules run first; optional model use is bounded behind a gateway and policy. Richer agent orchestration remains roadmap work. |
| Approval and governance | Typed policies, playbooks, proposals, and approval records; approval does not execute an action. |
| Guarded execution | Core intentionally ships no production executor. Portable executor/verifier protocols remain future, security-gated work. |
| Verification and learning | Explicit verification outcomes can create reusable confirmed memory; failed, unknown, or timed-out outcomes cannot become truth. |

The lifecycle remains **detect, triage, diagnose, plan, approve, remediate, verify, and learn**.
An adopter may use only the early stages; incremental adoption is part of the design.

## From recurring incidents to deterministic rules

The paper adds an explicit feedback path from verification and learning to deterministic policy:
when the same failure signature, diagnosis, and successful remediation recur, the pattern becomes
a candidate for a deterministic rule. Once reviewed and activated, that rule can handle the known
case before an LLM call, reducing token cost, latency, and nondeterminism.

This is a **promotion workflow**, not automatic truth-by-frequency:

1. Store each episode with bounded evidence, diagnosis, remediation, approval, and verification
   provenance.
2. Group only comparable episodes using a versioned, explainable signature.
3. Require a configurable recurrence threshold. Five verified recurrences is a useful example,
   not a universal default or a guarantee that the pattern is safe.
4. Generate a rule candidate containing its source episode IDs, proposed conditions, playbook,
   risk tier, expected evidence, and known counterexamples.
5. Replay the candidate against positive, negative, contradictory, and historical fixtures.
6. Require maintainer or adopter review before activation; high-risk behavior remains subject to
   approval and execution policy.
7. Monitor activated rules through immutable evaluation events and support revision, disabling,
   rejection, and rollback without rewriting incident history.

Frequency alone must never promote an unverified diagnosis, authorize an action, or turn a model
suggestion into confirmed truth. Promotion requires verification provenance, replay evidence,
bounded scope, and an accountable decision.

## Current implementation status

| Capability | Status |
| --- | --- |
| Deterministic-first diagnosis and explained rule matches | Implemented |
| Verification-confirmed and human-confirmed reusable memory | Implemented |
| Rejected, superseded, failed, unknown, and timed-out learning boundaries | Implemented |
| Deterministic replay evaluation for current contracts | Implemented |
| Recurrence analytics and explainable pattern grouping | Planned in Phase 3 |
| Rule-candidate generation with provenance and replay evidence | Planned in Phase 3 |
| Automatic activation of generated rules | Not implemented and not planned as an unreviewed default |
| Production remediation executor in core | Not implemented; core intentionally has none |

See the [phased roadmap](../../ROADMAP.md), especially Phase 3 rule analytics and memory feedback,
for the implementation sequence. Documentation and examples must keep this status distinction
visible as the project evolves.
