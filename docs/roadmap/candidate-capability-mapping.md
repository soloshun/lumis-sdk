# Candidate capability mapping

Date: 2026-07-17

This review maps thirty generally reusable candidate capabilities into the public SDK roadmap.
It is not an issue list or release promise. Each item must still pass standalone-use validation
and maintainer approval before its sprint creates implementation issues.

| # | Candidate | Planned placement | Sprint | Reason |
| --- | --- | --- | --- | --- |
| 1 | Model task/stage vocabulary | Core contract | 7 | Provider-neutral policy and audit vocabulary |
| 2 | Provider connection, model profile, stage route | Core contract | 7 | Portable composition without provider SDK types |
| 3 | Capability declaration/negotiation | Core contract/testkit | 7 | Deterministic preflight and fail-closed routing |
| 4 | Rich model-use policy | Core contract/application guard | 7 | Shared budgets across gateway implementations |
| 5 | Versioned prompt packages | Core document contract | 8 | Reproducible, reviewable prompt artifacts |
| 6 | Prompt renderer/injection boundaries | Core port/reference adapter | 8 | Safe deterministic composition; content remains project-owned |
| 7 | Credential references | Core value contract | 7 | Identifies ownership without carrying secrets |
| 8 | Deterministic model router | Core application service | 7 | Replayable route/fallback decisions |
| 9 | Provider-neutral invocation events | Core semantic event | 7/14 | Comparable audit metadata across adapters |
| 10 | Typed triage state machine | Core pure transition contract | 9 | Framework-neutral lifecycle semantics |
| 11 | Evidence plan/objectives | Core domain/port contracts | 9 | Inspectable evidence intent and bounds |
| 12 | Read-only agent tools | Core descriptors/testkit | 9 | Safely exposes evidence providers to runtimes |
| 13 | Agent budget/loop guards | Core application guards | 10 | Framework-independent termination and escalation |
| 14 | Grounding/citation validation | Core validation service | 10 | Evidence integrity regardless of provider |
| 15 | Model/tool conformance testkit | Core testkit | 10 | Offline adapter proof without paid keys |
| 16 | Evaluation dataset/evaluator API | Core contracts/reference evaluators | 11 | Portable quality and safety evidence |
| 17 | Evaluation promotion policy | Core contract | 11 | Transparent candidate/baseline decisions |
| 18 | Correlation graph primitives | Core contracts/reference scorer | 12 | Explainable cross-tool grouping without graph vendor |
| 19 | Causal/data-lineage graph primitives | Core contracts/reference traversal | 13 | Portable jobs/runs/assets/changes graph |
| 20 | Lineage provider capability | Core plugin capability + optional adapters | 13/17 | Vendor bindings remain outside core |
| 21 | Rule evaluation/analytics events | Core events/reducers | 14 | Immutable explainable local analytics |
| 22 | Memory retrieval feedback | Core events/reducers | 15 | Measures usefulness without rewriting truth |
| 23 | Semantic retrieval port | Core port + optional pgvector/provider packages | 15 | Strategy portability; exact/full-text stays available |
| 24 | Provenance/semantic audit events | Core events | 14 | Cross-capability causation and redaction-safe audit |
| 25 | Additional plugin capabilities | Core plugin protocol/testkit | 18 | Explicit capability and authority negotiation |
| 26 | Executor/verifier ports | Core protocol + sandbox examples only | 19 | Interoperability without default production authority |
| 27 | Signed envelope/replay primitives | Core transport-neutral contracts/test vectors | 20 | Runner/control-plane interoperability |
| 28 | Policy conformance/explanation | Core contract/testkit; optional OPA adapter | 20 | Equivalent fail-closed decisions across boundaries |
| 29 | Config migrations/doctor | Core config/CLI | 21 | Safe evolution and actionable diagnostics |
| 30 | Capability compatibility/deprecation | Core plugin/stability policy | 21 | Machine-readable ecosystem evolution |

## Optional package classification

| Package area | Earliest phase | Classification rule |
| --- | --- | --- |
| Pydantic AI bridge | Phase 2 | Adapter only; no framework type in domain or persistence |
| OpenRouter/OpenAI/Anthropic/OpenAI-compatible | After Sprint 7 | Independent provider packages with common conformance tests |
| OpenLineage/dbt/Airflow/Dagster/Prefect | Phase 3 | Lineage/evidence packages selected from demand |
| Alertmanager/Prometheus/OpenTelemetry/Sentry/CloudWatch | Phase 3 | Read-only bounded evidence packages |
| GitHub Actions/CI-CD | Phase 3 | Evidence and verifier packages; executor needs Phase 4 protocol |
| PostgreSQL full text/pgvector | Phase 3 | Optional strategy in the existing database package |
| OPA/Rego | Phase 4 | Policy adapter; core retains provider-neutral decision contract |
| Slack/Teams | Phase 4 | Notification/decision transport, never authoritative state by itself |
| S3-compatible object evidence | Phase 3 | Bounded references/reads, no arbitrary traversal |

## Product-only exclusions

Organizations, tenancy, RBAC/SSO/SCIM, hosted secret custody, billing, entitlements, managed model
catalogs, prompt-authoring UI, hosted evaluation jobs, SaaS retention/legal hold, OAuth setup UX,
runner fleets, customer networking, dashboards, support operations, and compliance administration
remain outside Lumis SDK. A generic contract may be reusable; the hosted implementation is not.
