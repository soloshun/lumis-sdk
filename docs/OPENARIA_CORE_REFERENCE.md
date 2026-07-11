# OpenARIA core reference

> **Canonical site/documentation handoff.** Use this file, the repository README, and the typed code contracts as the source of truth. Do not present roadmap features as implemented.

## Identity

- **ARIA** is the Agentic Recovery and Incident Automation research reference architecture.
- **OpenARIA** is its Apache-2.0 open-source Python implementation companion.

OpenARIA is deterministic-first, evidence-grounded, model-optional, local-first and vendor-agnostic.

## Promise

OpenARIA turns bounded incident evidence into structured diagnosis, human-readable reporting, and inspectable operational memory. It begins with Diagnosis-as-Code and grows toward guarded Healing-as-Code.

It does not replace a monitoring system or orchestrator. It does not require a model. It does not grant an LLM unrestricted production authority.

## Paper lifecycle and implementation status

| Stage | Current OpenARIA status |
| --- | --- |
| Detect | Local-log input and incident-source contracts; production detection remains external. |
| Triage | Deterministic classification, severity, and missing context. |
| Diagnose | Explainable rules; optional model gateway only after explicit policy and injection. |
| Plan | Recommendation-only `ActionPlan` and suggested playbooks. |
| Approve | Explicit approval state contract. |
| Remediate | No core executor. Future work requires RFC, allowlist, policy, audit, limits, and sandbox tests. |
| Verify | Verification result contract; no false recovery claim. |
| Learn | SQLite memory and human resolution; fuller truth-state persistence is roadmap work. |

## Architecture source

Read:

- [Architecture overview](architecture/overview.md)
- [Refactor audit](architecture/refactor-audit.md)
- [Migration plan](architecture/refactor-plan.md)
- [Configuration reference](configuration.md)
- [Threat model](safety/threat-model.md)
- [Roadmap](../ROADMAP.md)

## Public Python surface

### Domain

`openaria.domain` contains incidents, evidence, hypotheses, diagnoses, severity, diagnosis method, truth state, confirmed resolution, context, plans, approvals, verification, audit, and lifecycle results. Domain code imports no vendor SDK.

### Application

`openaria.application.DiagnosisService` runs deterministic diagnosis first. It reaches a model only for an unknown diagnosis when an enabled `ModelUsePolicy` and a `ModelGateway` are both supplied.

`openaria.application.run_guarded_lifecycle` coordinates context, diagnosis, proposal, approval, and verification without an executor or infrastructure adapter.

### Ports

`openaria.ports` defines model, memory, reporting, context, policy, approval, verification, and audit interfaces. Independent packages can implement them without changing the OpenARIA domain.

### Adapters

Reference adapters provide deterministic rules, SQLite local memory, and Markdown reports. Provider-specific connectors belong in separate packages when practical.

### Testkit

`openaria.testkit.FakeModelGateway` supports deterministic CI without credentials or live requests. Reusable adapter contract tests will expand in later milestones.

## Configuration

Projects use strict `openaria.dev/v1alpha1` `Project` and `DiagnosisRuleSet` documents. Unknown fields and unversioned proof-of-concept configuration are rejected, and JSON Schema is checked in.

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

Agno and OpenRouter are optional cookbook choices, not OpenARIA core dependencies. Each cookbook owns its synthetic fixtures, config, rules, knowledge, service, prompt policy, and provider integration.


## Site information architecture

1. Home / Why OpenARIA
2. Quick start
3. Concepts: Diagnosis-as-Code, Healing-as-Code, deterministic first, guarded recovery, memory
4. Architecture
5. Configuration
6. CLI
7. Python API
8. Ports and future plugins
9. Cookbooks
10. Safety
11. Contributing and governance
12. Roadmap
13. OpenARIA

The site must clearly label pre-alpha behavior, preserve the no-execution claim, and distinguish framework contracts from shipped adapters and roadmap plans.
