# Framework and cookbook architecture

This page explains one boundary within the project. For the complete core narrative, public API model, paper mapping, and documentation-site handoff, start with the [OpenARIA Core Reference](OPENARIA_CORE_REFERENCE.md).

## Purpose

OpenARIA is a lightweight, vendor-agnostic framework for diagnosing pipeline incidents. Its reusable core should not depend on a specific orchestrator, web server, model provider, or agent framework.

A cookbook is a separate runnable project that imports OpenARIA and demonstrates how an application can use those public interfaces. This keeps the core useful for different stacks while making the paper demonstration concrete and reproducible.

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

The `openaria.llm` and `openaria.lifecycle` modules are intentionally small public extension surfaces, not leftover application code. `llm` defines an optional provider-neutral gateway, structured response validation, and redaction; `lifecycle` defines typed contracts for context, policy, approval, planning, verification, and audit events. The initial cookbooks use configuration, diagnosis, reports, and local memory directly, while future adapters can implement these contracts without putting an agent or vendor SDK in the core package.

## Cookbook responsibilities

Agentic cookbooks are separate applications that use the core. Each contains its own optional dependencies, setup instructions, and synthetic data.

- A small FastAPI simulator exposes a synthetic pipeline incident and bounded context endpoints.
- An opt-in Agno agent uses OpenRouter only when a user supplies an API key and chooses a model.
- Agent tools call explicit cookbook adapters backed by OpenARIA's interfaces.
- The demo records a diagnosis, returns a proposed playbook, requests approval, and reads a synthetic verification result.
- No tool receives shell access, database-write access outside local OpenARIA memory, or unrestricted web access.

The cookbook must remain runnable without a live model call through fixtures and a deterministic mode. CI must never require an API key or make a billable request.

## Mapping to the ARIA reference architecture

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

1. `get_incident` and `get_context` retrieve bounded synthetic incident data.
2. `get_framework_diagnosis` runs the cookbook configuration through the core deterministic engine.
3. `read_runbook`, `read_playbook`, and `read_synthetic_code` read only cookbook-owned, allowlisted resources.
4. `record_framework_diagnosis` stores a local framework report and `export_analysis` stores the final LLM Markdown report.
5. `propose_playbook` and `request_approval` model a recommendation and explicit human decision boundary.

These tools model the investigation and governance loop, not autonomous execution. A proposed playbook is the terminal action for the first cookbook.

## Demo service and watcher

The FastAPI simulator is started manually by the cookbook user. The first agent run is a one-shot command against a chosen synthetic incident; this keeps the result reproducible and easy to review.

An optional watcher can follow later as a bounded polling command with an explicit maximum poll count. It must be opt-in, stop predictably, and only open or analyze synthetic incidents. A background daemon is not part of the initial proof.

## Build sequence

1. Add framework lifecycle contracts and the data-driven YAML configuration surface.
2. Move simple logs, rules, and resolution walkthroughs into cookbooks.
3. Build cookbook-owned synthetic data-pipeline and ML-regression fixture packs and FastAPI simulators on top of framework contracts.
4. Add opt-in Agno + OpenRouter applications with narrow tools.
5. Demonstrate recommendation, human approval boundaries, synthetic verification context, and memory update.

This sequence gives the cookbook something real to consume while keeping OpenARIA useful without the cookbook.
