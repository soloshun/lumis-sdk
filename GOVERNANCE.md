# Lumis SDK governance

Lumis SDK currently uses a benevolent-maintainer model. Solomon Eshun is the lead maintainer,
security contact, package owner, and final release authority. Review and merge access may be
delegated, but PyPI ownership, security embargo decisions, and stable-release approval remain
with the lead maintainer until this file records a successor or a multi-maintainer process.

## Decisions

Small, reversible changes use issues and pull requests. Cross-cutting changes require an RFC
before implementation, including new core ports, breaking domain or configuration changes,
plugin-system changes, execution capability, default model behavior, remote telemetry, and
governance or licensing changes. The lead maintainer resolves deadlocks after documenting the
trade-off in the issue, pull request, RFC, or an architecture decision record.

Accepted architectural decisions should be recorded in `docs/adr/` as the contributor base grows.

## Core and plugin ownership

- `lumis-sdk` core and packages published from this repository are official and maintained under
  this governance and security policy.
- An official optional plugin must live in the Lumis SDK organization/repository set, name its
  maintainers, pass the public contract suite, declare its authorities, and follow the SDK release
  and security process. Official does not mean installed by default.
- A community plugin is owned, supported, secured, versioned, and released by its publisher. It
  must not imply official endorsement or use reserved Lumis branding. Compatibility is a claim by
  that publisher unless this project records an independent verification.
- Inactivity, unresolved security risk, or an unavailable maintainer may move an official plugin
  to deprecated or archived status through a public issue and migration notice.

Contributions remain subject to the Apache-2.0 license, clean-room policy, and contributor
provenance declaration in `CONTRIBUTING.md`. Copyright remains with contributors unless a
separate written agreement says otherwise.

## Releases

Only the lead maintainer or an explicitly delegated release maintainer may publish releases.
Release credentials must not be shared through issues, pull requests, or repository files. The
release maintainer owns the checklist and evidence package; the lead maintainer makes the final
stable go/no-go decision. A failed gate cannot be silently waived: the decision record must name
the residual risk, scope, owner, and follow-up issue.
