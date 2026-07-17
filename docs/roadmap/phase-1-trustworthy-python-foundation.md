# Phase 1 — Trustworthy Python foundation

Sprints: 0–6

## Phase outcome

An independent Python application can install Lumis SDK, normalize a bounded incident, collect
typed evidence, diagnose deterministically, produce reports, retain explicit operational memory,
create a governed proposal, record approval and verification, and learn only confirmed outcomes.
The SDK is documented, security-reviewed, compatibility-governed, and distributable without a
Lumis account, model provider, or production executor.

## Delivered foundation

Sprints 0–5 delivered deterministic structured rules, bounded evidence, versioned reports, plugin
discovery, SQLite/PostgreSQL memory, webhook and HTTP evidence connectors, proposal governance,
explicit verification, truth-aware retrieval, and replay metrics through core `0.0.8` and plugin
`0.1.1` releases.

## Sprint 6 — Stable contracts, security, documentation, and adopters

**Outcome:** Phase 1 becomes a defensible stable Python foundation. Stability applies to a clearly
inventoried public surface; it does not promise that every experimental adapter or future recovery
protocol is frozen forever.

**Tracking:** epic #9. Split into implementation issues only when Sprint 6 begins.

- [x] **S6-01 Public API inventory:** classify imports, protocols, configuration, serialized
      documents, plugin metadata, CLI commands, and schemas as stable, provisional, or internal.
- [x] **S6-02 Configuration v1:** publish `lumis.dev/v1` project/rule/report/policy schemas, retain
      bounded `v1alpha1` reading for a documented transition, and provide deterministic migration
      plus validation tooling.
- [x] **S6-03 Compatibility and deprecation:** publish Python, config, persistence, plugin, CLI,
      and schema compatibility guarantees; add typed deprecation notices and contract tests.
- [x] **S6-04 Security closure:** perform an internal threat-model review, hostile-input audit,
      authority inventory, secret scan, dependency/license review, and public residual-risk log.
- [x] **S6-05 Release supply chain:** generate an SBOM, retain trusted-publisher attestations,
      document reproducible build inputs, verify sdist/wheel contents, and test clean installs on
      every supported Python version.
- [ ] **S6-06 Documentation system:** complete a navigable API index, concepts, configuration,
      plugin-author, migration, security, and maintainer guides suitable for a future docs site.
- [ ] **S6-07 Independent adoption evidence:** validate at least two non-Lumis paths—one core-only
      local workflow and one optional-plugin workflow—with reproducible fixtures and limitations.
- [ ] **S6-08 Relatable examples:** add or strengthen examples for data pipelines, ML quality,
      software delivery, webhook evidence, shared PostgreSQL memory, policy proposals, and
      verification replay; add Prometheus/Alertmanager and custom PostgreSQL-schema walkthroughs.
- [ ] **S6-09 Governance and support:** publish governance, code of conduct, security reporting,
      support boundaries, maintainer expectations, contributor DCO/provenance policy, and release
      ownership.
- [ ] **S6-10 Performance baseline:** record bounded-rule, serialization, SQLite retrieval, plugin
      discovery, and replay benchmark methodology without turning microbenchmarks into SLO claims.
- [ ] **S6-11 Release candidate:** publish a release candidate, run upgrade and plugin compatibility
      rehearsals, gather adopter/security feedback, and resolve or publicly accept findings.
- [ ] **S6-12 Stable release decision:** publish `1.0` only after all local gates and required
      external evidence pass; otherwise keep #9 open with explicit blockers.

### Acceptance evidence

- Public API and compatibility matrix with executable import/serialization checks.
- Generated v1 schemas, migration fixtures, and upgrade guide.
- Security review report, authority matrix, SBOM, provenance links, and residual risks.
- Python 3.11–3.13 clean-install and plugin coexistence results.
- Two independent adoption reports and runnable example smoke tests.
- Governance/support files, documentation index, video scripts, and benchmark report.
- Explicit release-candidate and stable-release go/no-go decisions.

### External gates

The project must not manufacture external evidence. An independent security review and adopter
feedback can be prepared and tracked by maintainers, but Sprint 6 remains open until the required
evidence exists or the maintainer explicitly accepts a narrower `1.0` scope and documents the
residual risk.

## Phase 1 exit criteria

- Stable surfaces and experimental surfaces are distinguishable in code and documentation.
- Configuration v1 has a tested migration from every published alpha shape.
- No known critical/high security issue or unresolved authority ambiguity remains.
- Release artifacts are attested, inventoried, reproducibly built, and publicly installable.
- At least two standalone use cases have reproducible adoption evidence.
- Phase 2 may extend model/agent contracts without breaking Phase 1 deterministic use.
