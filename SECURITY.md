# Security Policy

## Supported versions

OpenARIA is pre-release software. Security fixes are applied to the latest development version only.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or exposed credential. Until a dedicated private reporting channel is configured, contact the repository maintainers privately through the repository owner's published contact channel. Include a clear description, reproduction steps, impact, and any suggested mitigation.

We will acknowledge the report, investigate it, and coordinate a fix before public disclosure where appropriate.

## Secrets

Never commit API keys, access tokens, private URLs, production logs, or customer data. Future optional model examples must read credentials from environment variables and must not make live calls in CI.
