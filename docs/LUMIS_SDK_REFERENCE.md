# Lumis SDK core reference

## Identity

- **Agentic recovery and incident response** is the technology-flexible reference architecture proposed by the accompanying research.
- **Lumis SDK** is its Apache-2.0 open-source Python implementation companion.

Lumis SDK is deterministic-first, evidence-grounded, model-optional, local-first and vendor-agnostic.

## Promise

Lumis SDK turns bounded incident evidence into structured diagnosis, human-readable reporting, and inspectable operational memory. It begins with Diagnosis-as-Code and grows toward guarded Healing-as-Code.

It does not replace a monitoring system or orchestrator. It does not require a model. It does not grant an LLM unrestricted production authority.

## Paper lifecycle and implementation status

| Stage | Current Lumis SDK status |
| --- | --- |
| Detect | Local-log input and incident-source contracts; production detection remains external. |
| Triage | Deterministic classification, severity, and missing context. |
| Diagnose | Explainable rules; optional model gateway only after explicit policy and injection. |
| Plan | Recommendation-only `ActionPlan` and suggested playbooks. |
| Approve | Explicit approval state contract. |
| Remediate | No core executor. Future work requires RFC, allowlist, policy, audit, limits, and sandbox tests. |
| Verify | Verification result contract; no false recovery claim. |
| Learn | SQLite and optional PostgreSQL operational memory retain explicit resolutions; verification-aware promotion and replay evaluation remain roadmap work. |

## Architecture source

Read:

- [Architecture overview](architecture/overview.md)
- [Configuration reference](configuration.md)
- [Threat model](safety/threat-model.md)
- [Roadmap](../ROADMAP.md)

## Public Python surface

### Domain

`lumis_sdk.domain` contains incidents, evidence, hypotheses, diagnoses, severity, diagnosis method, truth state, confirmed resolution, context, plans, approvals, verification, audit, and lifecycle results. Domain code imports no vendor SDK.

### Application

`lumis_sdk.application.DiagnosisService` runs deterministic diagnosis first. It reaches a model only for an unknown diagnosis when an enabled `ModelUsePolicy` and a `ModelGateway` are both supplied.

`lumis_sdk.application.EvidenceService` collects bounded typed evidence through provider ports,
with deadlines, filtering, duplicate handling, truncation, redaction, and structured failures.

`lumis_sdk.application.run_guarded_lifecycle` coordinates context, diagnosis, proposal, approval, and verification without an executor or infrastructure adapter.

### Ports

`lumis_sdk.ports` defines evidence, model, memory, reporting, context, policy, approval,
verification, and audit interfaces. Independent packages can implement them without changing the
Lumis SDK domain.

### Adapters

Reference adapters provide deterministic rules, SQLite local memory, bounded local JSON evidence,
Markdown or versioned JSON reports, and metadata-first plugin discovery. Provider-specific
connectors belong in separate packages when practical. The repository includes an independently
installable PostgreSQL memory plugin proof without adding its driver to core.

### Testkit

`lumis_sdk.testkit` provides deterministic model and evidence fakes, incident/evidence fixtures,
and reusable evidence-collection, JSON-report, and asynchronous memory-store contract assertions
without credentials or live
requests. It also provides plugin manifest/factory fixtures and a reusable factory contract
assertion for independently packaged adapters.

## Configuration

Projects use strict `lumis.dev/v1alpha1` `Project` and rule documents. Project configuration can
select local JSON evidence and Markdown or JSON reporting. Unknown fields and unversioned
proof-of-concept configuration are rejected, and checked JSON Schemas cover configuration, rules,
and reports.

## Truth and confidence

Facts are supported observations. Evidence points to supplied context. Hypotheses remain uncertain and carry confidence. Missing evidence is visible. A human resolution changes local memory from `unconfirmed_hypothesis` to `human_confirmed`; model text never performs that transition.

Rule confidence is authored calibration, not a framework-computed probability and not authorization to act.

## Safety and privacy

- Local deterministic use has no network or credential requirement.
- Configuration and CLI log reads are bounded.
- Optional model context is minimized and conservatively redacted.
- Logs, code, runbooks, tickets, and model output are untrusted data.
- No remote telemetry is emitted by default.
- No core shell/cloud/database action executor exists.

## Cookbooks

The synthetic cookbooks demonstrate three paper domains:

- data-pipeline investigation;
- ML regression monitoring;
- software-delivery CI and infrastructure validation.

Agno and OpenRouter are optional cookbook choices, not Lumis SDK core dependencies. Each cookbook owns its synthetic fixtures, config, rules, knowledge, service, prompt policy, and provider integration.
