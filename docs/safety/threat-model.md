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
| Hostile or oversized YAML | Safe loader, strict schemas, one-MiB file limit, alias rejection, 64-node nesting limit, and hostile-input tests. | Broader parser fuzz/property testing. |
| Oversized logs | CLI ten-MiB limit. | Streaming/slicing and configurable bounded readers. |
| Path traversal | Cookbook file endpoints resolve and enforce a fixed root; config paths are explicit local authority. | Add dedicated security tests for all file adapters. |
| Unsafe Markdown | Reports are deterministic text, not executed HTML. | Escaping policy for future web renderers. |
| Model hallucination | Schema validation, evidence separation, deterministic fallback, unconfirmed truth state. | Citation validation and evaluation metrics. |
| Unapproved actuation | No core executor; versioned proposals pin evidence, policy/playbook revisions, bounded parameters, risk, expiry, and approval state. High risk never auto-approves. | Any executor requires a separate RFC, signatures, limits, deployment authorization, audit, idempotency, and verification. |
| Plugin supply chain | Static strict manifests, metadata-only discovery, compatibility checks, isolated failures, support labels, explicit loading, and default-denied sensitive authorities. | Provenance/signature policy, package allowlists, and isolated-process loading where adopters require stronger containment. |
| Shared-memory credential or SQL abuse | PostgreSQL uses an environment-variable reference, validated/quoted schema, fixed statements, bounded candidates, explicit plugin authorities, and no execution surface. | Deployment TLS, rotation, least-privilege roles, retention, backup, and network policy remain adopter responsibilities. |
| Memory poisoning or false learning | Episode IDs and truth transitions are idempotent, conflicting reuse fails closed, only explicit human/verification confirmation is reusable, non-passing verification escalates, and rejected/superseded memory is filterable. | Adopters must govern retention, reviewer identity, verifier trust, and corpus provenance. |
| Forged, replayed, or hostile webhooks | Exact-byte HMAC, constant-time comparison, timestamp skew, strict delivery IDs, injectable atomic replay guard, unique-key JSON, depth/node limits, and payload cap. | Deployments must add TLS, rate limits, durable shared replay storage, source policy, and safe HTTP responses. |
| Connector SSRF, credential leakage, or oversized responses | HTTP evidence requires HTTPS and exact origin allowlisting, rejects redirects/URL credentials, references token env vars, minimizes outbound fields, bounds retries/time/bytes, and returns structured failures. | Deployment DNS/network egress policy, token rotation, endpoint trust, and provider-specific schemas remain adopter responsibilities. |
| Silent telemetry | No remote telemetry adapter or default export. | Document explicit opt-in if optional Logfire/OpenTelemetry is added. |

## Security invariants

1. Deterministic local use requires no credential or network call.
2. A model response is never a confirmed resolution or executable action.
3. High-risk proposals cannot auto-approve, and approval never grants core execution authority.
4. Verification must follow any external execution before verification-confirmed recovery.
5. Installing or discovering a plugin grants no network, filesystem, secret, model, or execution
   authority.

The detailed [authority inventory and residual-risk review](security-review.md) records the
Sprint 6 review scope, local evidence, external gate, and adopter-owned controls.
