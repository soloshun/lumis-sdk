# Lumis SDK roadmap

## v0.1 - Diagnosis-as-Code foundation

Local logs, deterministic rules, Pydantic models, Markdown reports, SQLite memory, lexical search, optional model boundary, lifecycle contracts, and synthetic cookbooks.

## v0.2 - Structured rules and evidence

Versioned strict configuration, rule IDs/versions/priorities, explainable matches, evidence-provider port, JSON reporting, doctor and validation commands, generated schema, and stable testkit.

## v0.3 - Plugin SDK

RFC-governed entry-point discovery, manifests, compatibility checks, contract tests, generic webhook, and one independently packaged evidence connector.

## v0.4 - Policy and playbook proposals

Typed versioned playbooks, risk tiers, proposals, approval contracts, and sandbox cookbook. No default production execution.

## v0.5 - Verification and learning

Verifier port, explicit truth states persisted in memory, verified outcomes, transparent retrieval scoring, and replay evaluation tools.

## v1.0 criteria

Stable contracts and config v1, upgrade guide, security review, comprehensive docs, multiple independent adopters, tested plugin ecosystem, and no unresolved lifecycle ambiguity.

## Delivery sprint sequence

Dates are planning targets rather than release promises. The private GitHub project keeps the
durable roadmap epics, while only the active sprint is split into granular implementation work.

| Sprint | Target window | Outcome | Roadmap issues |
| --- | --- | --- | --- |
| Sprint 0 - Maintainer baseline | Complete | Open-source workflow, structured deterministic rules, and the `0.0.2` release. | #1 |
| Sprint 1 - Evidence and reporting | Complete | Bounded typed evidence, versioned JSON reports, doctor checks, stable testkit contracts, and releases `0.0.3`/`0.0.4`. | #4, #19 |
| Sprint 2 - Plugin SDK | In progress | Governed discovery, manifests, compatibility checks, and plugin contract tests. | #5 |
| Sprint 3 - Durable memory and connector proof | 2026-10-05 to 2026-11-13 | Optional shared memory and one independently packaged evidence path. | #2, #6 |
| Sprint 4 - Policy and playbook proposals | 2026-11-16 to 2027-01-15 | Typed, evidence-linked, approval-aware proposals with no core execution authority. | #7 |
| Sprint 5 - Verification and learning | 2027-01-18 to 2027-03-19 | Explicit verification truth, transparent retrieval, and replay evaluation. | #8 |
| Sprint 6 - v1 stabilization | 2027-03-22 to 2027-06-30 | Stable contracts, secure releases, complete docs, and independent adoption evidence. | #9 |

Feature and fix branches start from `dev` and return to `dev` through review. Reviewed release
changes are promoted from `dev` to `main`; package publication remains an explicit maintainer
release action.
