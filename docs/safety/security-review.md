# Sprint 6 security and supply-chain review

Status: internal review complete for the current Phase 1 implementation; independent external
review pending. Last updated: 2026-07-17.

This record is evidence for the stable-release decision, not a claim that the SDK or its
dependencies are vulnerability-free. Findings must be updated when authority, dependencies,
wire formats, or execution behavior change.

## Scope and evidence

| Area | Review evidence | Result |
| --- | --- | --- |
| Core | Domain, application, ports, adapters, config, CLI, and testkit reviewed against `threat-model.md`. | No core executor, implicit model call, or default network telemetry found. |
| Configuration | Bounded YAML/JSON loading, strict models, path behavior, schemas, and migration. | One-MiB limit, safe construction, aliases rejected, depth capped at 64, mixed versions rejected. |
| Plugins | Metadata discovery, compatibility, loading policy, optional package manifests, and coexistence. | Discovery grants no authority; clean coexistence is tested; loading is explicit and default-deny. |
| Connectors | Webhook, HTTP JSON evidence, and PostgreSQL memory hostile-input suites. | Existing caps, allowlists, secret references, replay checks, fixed SQL, and timeouts retained. |
| Recovery | Proposal, approval, verification, learning, and replay contracts. | No execution surface; high risk cannot auto-approve; non-passing verification cannot become truth. |
| Dependencies | Locked audit, PR dependency review, license inventory, Dependabot, and Bandit. | No known audit finding at review time; future moderate-or-higher additions fail PR review. |
| Secrets | Repository history/content scan in CI plus environment-variable secret references. | Automated scan added; plaintext credentials remain prohibited. |
| Release | Restricted sdist contents, archive path/content validation, deterministic rebuild comparison, clean installs, SBOM, and attestations. | Workflow gate implemented; each release run must retain its own evidence links. |

## Runtime authority inventory

| Component | Network | Filesystem | Secrets | Model | Execution | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| Core deterministic diagnosis | No | Supplied in-memory values only | No | No | No | Pure domain/application path. |
| Reference CLI | No by default | Explicit config, log, report, and SQLite paths | No plaintext config secrets | No provider composed | No | User grants local paths at invocation/configuration. |
| Local JSON evidence | No | Explicit configured JSON path | No | No | No | Item/character/time limits and redaction. |
| Model gateway port | Adapter-defined | No core grant | Adapter-defined | Explicit opt-in | No | Policy and injected adapter both required. |
| Plugin discovery | No | Installed distribution metadata | No | No | No | Does not import plugin code. |
| Plugin loading | Plugin-declared | Plugin-declared | Plugin-declared | Plugin-declared | Default denied | Caller policy must allow every capability/authority. |
| HTTP JSON evidence plugin | Allowlisted HTTPS origin | No general access | Token environment reference | No | No | Redirects rejected; requests/responses bounded. |
| PostgreSQL memory plugin | Configured database only | No general access | Connection URL environment reference | No | Fixed SQL only | Schema validated/quoted; retrieval bounded. |
| Webhook normalizer | Receives supplied bytes; no outbound call | No | HMAC verifier receives secret | No | No | Size/depth/node/skew/replay boundaries. |
| Proposal/approval/verification | No | Adapter-defined persistence | No core secret | No required model | No executor | Approval never becomes execution authority. |

## Dependency and license review

Core runtime dependencies are Pydantic (MIT), PyYAML (MIT), and Typer (MIT), with their locked
transitive dependencies under permissive or MPL-2.0/PSF-2.0 terms. The HTTP plugin adds HTTPX
and transitive BSD/MIT/MPL-2.0 dependencies. The PostgreSQL plugin adds Psycopg under
LGPL-3.0-only as an optional dynamically used adapter dependency; maintainers and adopters must
review that choice for their distribution model. This is an engineering inventory, not legal
advice.

PR dependency review audits the full locked environment and denies GPL-3.0, AGPL-3.0, and
SSPL-1.0 license identifiers across core and both plugin environments. `uv audit --locked` also
runs on pushes, pull requests, and weekly. GitHub's graph-based dependency-diff review can be
added when the repository dependency graph is enabled. License metadata is generated with
`pip-licenses`; the release SBOM is the artifact-specific inventory.

## Residual risks and adopter controls

- Model output, logs, tickets, code, and runbooks remain untrusted. Adopters must constrain any
  model adapter and must not convert model confidence into authorization.
- Plugin code runs in the application process after explicit loading. Stronger isolation,
  package allowlists, signatures, and provenance policy are deployment choices until a future RFC.
- HTTP origin allowlisting does not replace DNS/egress policy, endpoint trust, token rotation, TLS
  interception policy, or provider-specific response validation.
- PostgreSQL deployments own TLS, least-privilege roles, rotation, retention, backup, row-level
  tenancy, and network policy.
- SQLite files and generated reports inherit host filesystem permissions; core does not encrypt
  them at rest.
- YAML aliases are intentionally unsupported. JSON duplicate-key rejection and broad parser fuzzing
  remain follow-up hardening work.
- Signed build provenance proves how GitHub Actions produced an artifact; it does not prove that
  source logic is safe or that an external reviewer approved it.

## External review gate

No independent security assessment has been supplied as of 2026-07-17. That gate remains open in
epic #9 and issue #55. A release candidate may be built and reviewed, but maintainers must not mark
the external gate complete or claim independent validation without a named report, scope, date,
findings disposition, and public-safe evidence link.

## Release evidence checklist

For every candidate/stable release, retain:

- successful Python 3.11–3.13 clean wheel and sdist install jobs;
- core and optional-plugin contract/coexistence results;
- dependency audit, dependency review, Bandit, and secret-scan results;
- artifact content validation and matching deterministic rebuild digests;
- downloadable SPDX SBOM and GitHub provenance/SBOM attestation URLs;
- TestPyPI/PyPI installed-package verification;
- unresolved findings and an explicit go/no-go decision.
