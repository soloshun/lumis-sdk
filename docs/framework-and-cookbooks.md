# Framework and cookbook architecture

This page explains one boundary within the project. For the complete core narrative, public API model, and paper mapping, start with the [Lumis SDK reference](LUMIS_SDK_REFERENCE.md).

## Purpose

Lumis SDK is a lightweight, vendor-agnostic framework for building guarded incident-recovery workflows. Its current implementation is diagnosis-centered, while its contracts deliberately leave room for policy-controlled planning, approval, verification, and learning. The reusable core does not depend on a specific orchestrator, web server, model provider, or agent framework.

A cookbook is a separate runnable project that imports Lumis SDK and demonstrates how an application can use those public interfaces. This keeps the core useful for different stacks while making the paper demonstration concrete and reproducible.

## Core framework responsibilities

The core owns stable, typed interfaces and safe default behavior:

- Normalize incidents from a manual log, webhook adapter, or later connector.
- Represent evidence, triage, diagnosis, reports, and incident memory.
- Store local incident memory and retrieve it using a transparent baseline search.
- Provide a deterministic diagnosis path that works without a model provider.
- Define a provider-neutral model-gateway boundary, redaction, and structured-output validation.
- Define lifecycle contracts for context retrieval, policy decisions, approval, planning, verification, and audit events.

The core does **not** own a live agent, a cloud account, a perpetual monitor, production credentials, direct remediation access, synthetic business scenarios, or project-specific rules/playbooks.

## Framework extension points

The canonical extension surfaces are `lumis_sdk.ports` and `lumis_sdk.domain`. Ports cover models, memory, reporting, context, policy, approval, verification, and audit. The `lumis_sdk.application` package composes these interfaces without importing provider SDKs. Model providers implement `ModelGateway`; redaction lives in `lumis_sdk.security`; local implementations live in `lumis_sdk.adapters`.

## Cookbook responsibilities

Agentic cookbooks are separate applications that use the core. Each contains its own optional dependencies, setup instructions, and synthetic data.

- A small FastAPI simulator exposes a synthetic pipeline incident and bounded context endpoints.
- An opt-in Agno agent uses OpenRouter only when a user supplies an API key and chooses a model.
- Agent tools call explicit cookbook adapters backed by Lumis SDK's interfaces.
- The demo records a diagnosis, returns a proposed playbook, requests approval, and reads a synthetic verification result.
- No tool receives shell access, database-write access outside local Lumis SDK memory, or unrestricted web access.

The cookbook must remain runnable without a live model call through fixtures and a deterministic mode. CI must never require an API key or make a billable request.

## Mapping to the reference architecture

The cookbook simulates the paper's seven logical layers. The agentic reasoning step is Layer 4; approval and governance are Layer 5.

| Paper layer | Cookbook demonstration | Core boundary |
| --- | --- | --- |
| 1. Existing pipeline estate | Cookbook-owned synthetic data or ML pipeline failure | Normalized `IncidentInput` |
| 2. Telemetry and signals | Cookbook-owned logs, metrics, schema snapshot, and lineage snapshot | Context-provider contract |
| 3. Incident memory and knowledge | Local SQLite incident memory and cookbook runbook/playbook | Memory-store contract |
| 4. Deterministic policy and agentic reasoning | Cookbook YAML rules first; optional Agno diagnosis agent for ambiguous context | Diagnosis, model-gateway, and policy contracts |
| 5. Approval and governance | Cookbook-owned explicit human approval prompt or fixture decision | Approval and audit contracts |
| 6. Guarded execution | No production execution; a cookbook proposal only | Action-plan contract that cannot execute commands |
| 7. Verification and learning | Cookbook-owned synthetic verification result and memory update | Verifier and memory-store contracts |

## Agent tools

The agent should use narrow, named tools rather than one unrestricted context dump:

1. `get_incident` and `get_investigation_guide` retrieve bounded incident data and the exact identifiers available for that scenario.
2. `get_context` retrieves only guide-listed synthetic context, while typed parameters prevent guessing known context, code, or knowledge names.
3. `get_framework_diagnosis` runs the cookbook configuration through the core deterministic engine.
4. `read_runbook`, `read_playbook`, and `read_synthetic_code` read only cookbook-owned, allowlisted resources.
5. The deterministic runner alone calls `record_framework_diagnosis` for a known rule match. An unknown-case agent may call `export_analysis` once to create a simple named Markdown report inside its local report directory.
6. `propose_playbook` and `request_approval` model a recommendation and explicit human decision boundary.

The agent has no tool that can create a deterministic report. Its export tool can only create a named Markdown report inside the cookbook's local report directory. These tools model the investigation and governance loop, not autonomous execution. A proposed playbook is the terminal action for the first cookbook.

## Demo service and watcher

The FastAPI simulator is started manually by the cookbook user. The first agent run is a one-shot command against a chosen synthetic incident; this keeps the result reproducible and easy to review.

An optional watcher can follow later as a bounded polling command with an explicit maximum poll count. It must be opt-in, stop predictably, and only open or analyze synthetic incidents. A background daemon is not part of the initial proof.

## Build sequence

1. Define framework lifecycle contracts and a versioned YAML configuration surface.
2. Keep logs, rules, runbooks, prompts, and synthetic scenarios in consuming projects or cookbooks.
3. Build data, ML, and software-delivery demonstrations on the public ports and domain models.
4. Add opt-in Agno + OpenRouter applications through the provider-neutral model boundary.
5. Demonstrate recommendations, approval boundaries, verification context, and human-confirmed learning without production execution.

This sequence gives the cookbook something real to consume while keeping Lumis SDK useful without the cookbook.
