# Lumis SDK open-source architecture and contribution guide

Date: 2026-07-17

Status: Phase 1 foundation released through core `0.0.8`; Sprint 6 stable-contract qualification
is planned. This document supersedes the original pre-alpha planning guide where implementation
has moved on.

## Project purpose

Lumis SDK is the Apache-2.0 Python implementation companion to the agentic self-healing research.
It packages vendor-neutral contracts, deterministic reference behavior, optional adapter
boundaries, reusable tests, and synthetic examples for guarded incident response and pipeline
recovery.

The SDK must remain useful without Lumis, a cloud account, a model provider, or production
credentials. Lumis is one product built on these contracts; it does not own or narrow them.

## Ownership boundary

Core may include provider-neutral domain models, pure invariants, configuration/schema helpers,
application services, extension ports, deterministic/local reference adapters, CLI composition,
redaction, canonical serialization, testkit fixtures, and synthetic/public cookbooks.

Optional packages contain vendor, framework, protocol, cloud, database extension, orchestration,
or heavy runtime bindings. They declare authority and compatibility and pass public contracts.

Hosted tenancy, users, RBAC, billing, entitlements, encrypted secret custody, managed connectors,
runner fleets, dashboards, approval workflow ownership, enterprise controls, and support operations
belong to products such as Lumis.

## Dependency and authority rules

```text
entry points -> application -> domain
                       \-> ports <- adapters/plugins
```

- Domain imports only the standard library and Pydantic.
- Application services coordinate contracts; they do not import vendor SDKs.
- Ports define replaceable capabilities and failure semantics.
- Core adapters are deterministic/local references; provider adapters are optional packages.
- Installing or discovering a plugin grants no network, filesystem, secret, model, or execution
  authority.
- Model output remains a hypothesis or recommendation, never confirmation or authorization.
- Core has no default production executor. Future execution protocols require RFC, policy,
  approval, idempotency, rate/impact bounds, signing, independent verification, and audit.

## Public contract families

| Family | Current responsibility |
| --- | --- |
| Incident/evidence/diagnosis | Bounded inputs, explicit facts/hypotheses, deterministic rules, reports |
| Memory/truth | SQLite and optional PostgreSQL, confirmation/rejection/supersession, explained retrieval |
| Plugins | Metadata-first discovery, compatibility, support, capability, and authority checks |
| Policy/proposals | Versioned playbooks/policies, bounded parameters, expiry, approval decisions, no execution authority |
| Verification/learning | Explicit outcomes, escalation, confirmed-only reuse, deterministic replay |
| Model boundary | Optional gateway and policy; richer routing/prompt/agent contracts remain Phase 2 |

Sprint 6 will inventory which imports, documents, protocols, schemas, CLI behavior, and persistence
shapes become stable in `1.0`. Anything not listed as stable remains provisional or internal.

## Contribution placement

Before writing code, classify the proposal:

1. **Core:** provider-neutral, broadly reusable, bounded, safe without hosted infrastructure.
2. **Official optional package:** provider/runtime binding with maintainer ownership and contracts.
3. **Community package:** external ownership using public contracts; visibility is not endorsement.
4. **Example/cookbook:** project-specific scenario, prompt, rule, runbook, or composition.
5. **Product-only:** tenancy, hosted operations, commercial administration, or managed workflow.

Substantial new ports, breaking contracts, plugin changes, model defaults, telemetry, governance,
or execution authority require an RFC and threat-model update before implementation.

## Required change evidence

- Unit/contract/integration/replay/hostile-input tests proportional to risk.
- No live credentials, private data, paid API, or production side effect in CI.
- Checked schemas and migration fixtures for serialized behavior.
- API/config/plugin/cookbook documentation and changelog updates.
- Compatibility, deprecation, security, and authority analysis.
- Runnable written example; important adoption paths also receive a reproducible video script.

## Branch, review, and release workflow

- Branch from `dev`; feature/fix/docs PRs target `dev`.
- Review architecture and authority before implementation detail.
- Required checks include supported Python versions, typing, tests, schema drift, dependency audit,
  SAST, package builds, and clean wheel installation.
- Promote reviewed `dev` to `main` in a separate release PR.
- Publish through trusted publishing, TestPyPI first when metadata changes, then PyPI.
- Verify public installation and plugin coexistence before closing release work.

## Roadmap and governance

The [phased roadmap](../../ROADMAP.md) is the public planning source. Future phases remain
documentation-only until one sprint is approved and split into issues. Maintainers control
branding, release authority, official-package status, security decisions, and roadmap promotion;
contributors are welcome across code, contracts, testkit, adapters, examples, docs, and RFCs.

Use only original code, public specifications, and synthetic/public data. Never contribute client,
employer, or proprietary product implementation material.
