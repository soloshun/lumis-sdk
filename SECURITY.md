# Security Policy

## Supported versions

Lumis SDK is pre-release software. Security fixes are applied to the latest development version only.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or exposed credential. Until a dedicated private reporting channel is configured, contact the repository maintainers privately through the repository owner's published contact channel. Include a clear description, reproduction steps, impact, and any suggested mitigation.

The lead maintainer named in `GOVERNANCE.md` owns triage and disclosure, and may delegate a
private investigation to a release maintainer. We will acknowledge the report, investigate it,
and coordinate a fix before public disclosure where appropriate. No fixed response SLA is
promised until a dedicated private reporting channel and security team are established.

## Secrets

Never commit API keys, access tokens, private URLs, production logs, or customer data. Future optional model examples must read credentials from environment variables and must not make live calls in CI.

## Trust boundaries

Logs, code, runbooks, tickets, configuration obtained from elsewhere, and model output are untrusted input. Do not treat model-generated text or rule confidence as authorization to act. Lumis SDK core intentionally ships no unrestricted shell, cloud, database, or remediation executor.

Local deterministic use makes no network request and needs no credentials. Optional provider adapters must be explicitly installed and configured, minimize exported context, apply redaction, document retention behavior, and enforce time and size bounds. See the [threat model](docs/safety/threat-model.md) and [security, authority, and residual-risk review](docs/safety/security-review.md) for the maintained assumptions and open external-review gate.
