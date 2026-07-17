# Phase 1 standalone adoption evidence

Status: maintainer-reproduced, non-Lumis paths. Last reproduced: 2026-07-17.

These paths demonstrate that the repository can be used without the Loomis/Lumis hosted product.
They are reproducible project evidence, not independent third-party testimonials. External adopter
feedback remains an open gate under epic #9.

## Path A: core-only local diagnosis

An adopter supplies one synthetic log and project-owned rule, runs the installed `lumis` CLI, and
receives a Markdown report plus local SQLite incident memory.

```bash
uv sync --frozen --all-groups
uv run lumis doctor --config cookbook/simple-log-diagnosis/lumis/lumis.yml
uv run lumis diagnose --config cookbook/simple-log-diagnosis/lumis/lumis.yml
```

Expected evidence:

- configuration and rules validate with `lumis.dev/v1`;
- diagnosis is deterministic and no network credential is requested;
- the report distinguishes evidence, hypothesis, and unconfirmed truth;
- output and memory remain under the cookbook directory and can be deleted locally.

Limits: the reference input is a bounded local log, matching is only as useful as the adopter's
rules, SQLite is local-process storage, and no remediation action is executed.

## Path B: independently packaged connector

This path installs/composes the optional HTTP JSON evidence plugin, but uses `httpx.MockTransport`
and synthetic fixtures so the smoke path remains offline.

```bash
PYTHONPATH=packages/lumis-sdk-http-json-evidence/src \
  uv run --python 3.12 --with 'httpx>=0.28,<1' \
  python cookbook/webhook-http-evidence/demo.py
```

Expected output contains:

```text
incident=fixture-pipeline evidence=1 detail=The fixture schema removed customer_id.
```

The path exercises exact-byte HMAC verification, timestamp skew, delivery replay claiming,
versioned plugin configuration, explicit plugin creation, allowlisted HTTPS request composition,
bounded evidence collection, and structured output without a live endpoint.

Limits: `MockTransport` proves composition and contracts, not DNS, TLS, remote availability,
provider identity, rate limiting, or production replay storage. Deployments own those controls.

## Reproduction in CI

Core tests cover the local adapters and historical compatibility fixtures. The HTTP plugin job
runs its independent contract and offline demo. The plugin-coexistence job builds core and both
optional plugins as wheels, installs them in an empty environment, and verifies metadata discovery
without importing plugin modules. PostgreSQL behavior requiring a database is exercised against a
temporary PostgreSQL service in its own job.
