# Lumis SDK threat model

## Assets

Incident evidence, credentials, local files, operational memory, diagnosis integrity, rules, playbooks, reports, plugin packages, and any future approved action.

## Trust boundaries

- Logs, webhook payloads, tickets, runbooks, source code, and model output are untrusted data.
- Configuration and plugins are trusted only after local review and validation.
- Model providers and agent frameworks are optional external processors.

## Principal threats and current controls

| Threat | Current control | Remaining work |
| --- | --- | --- |
| Prompt injection in evidence | Evidence is passed as data; model has no core execution tools; cookbooks use bounded tools. | Add adversarial replay/evaluation corpus. |
| Secret leakage | Conservative recursive redaction and explicit model opt-in. | Organization-specific redactors and provider policy adapters. |
| Hostile or oversized YAML | `safe_load`, strict schemas, one-MiB limit. | Alias/depth limits and fuzz/property testing. |
| Oversized logs | CLI ten-MiB limit. | Streaming/slicing and configurable bounded readers. |
| Path traversal | Cookbook file endpoints resolve and enforce a fixed root; config paths are explicit local authority. | Add dedicated security tests for all file adapters. |
| Unsafe Markdown | Reports are deterministic text, not executed HTML. | Escaping policy for future web renderers. |
| Model hallucination | Schema validation, evidence separation, deterministic fallback, unconfirmed truth state. | Citation validation and evaluation metrics. |
| Unapproved actuation | No core executor; application lifecycle is recommendation-only. | Any executor requires RFC, typed allowlist, signatures, limits, approval, audit, idempotency, and verification. |
| Plugin supply chain | Static strict manifests, metadata-only discovery, compatibility checks, isolated failures, support labels, explicit loading, and default-denied sensitive authorities. | Provenance/signature policy, package allowlists, and isolated-process loading where adopters require stronger containment. |
| Shared-memory credential or SQL abuse | PostgreSQL uses an environment-variable reference, validated/quoted schema, fixed statements, bounded candidates, explicit plugin authorities, and no execution surface. | Deployment TLS, rotation, least-privilege roles, retention, backup, and network policy remain adopter responsibilities. |
| Memory poisoning or false learning | Episode IDs are idempotent, conflicting reuse fails closed, truth state is explicit, and resolutions cannot target absent incidents. | v0.5 adds verification-aware promotion, supersession, rejection, and replay evaluation. |
| Silent telemetry | No remote telemetry adapter or default export. | Document explicit opt-in if optional Logfire/OpenTelemetry is added. |

## Security invariants

1. Deterministic local use requires no credential or network call.
2. A model response is never a confirmed resolution or executable action.
3. High-risk or irreversible actions cannot be introduced without human approval policy.
4. Verification must follow any future execution before confirmed recovery.
5. Installing or discovering a plugin grants no network, filesystem, secret, model, or execution
   authority.
