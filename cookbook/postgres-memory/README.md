# Shared PostgreSQL memory cookbook

This synthetic cookbook proves that independently running processes can share one explicit Lumis
SDK operational-memory episode. PostgreSQL and its driver remain optional and outside core.

The writer saves an unconfirmed episode and then records a human-confirmed resolution. The reader
starts as a separate process, retrieves the same episode, and prints transparent ranking reasons.
Running the reader again demonstrates that the data survives process restart.

```bash
docker compose -f cookbook/postgres-memory/compose.yml up \
  --build --exit-code-from reader
docker compose -f cookbook/postgres-memory/compose.yml run --rm reader
docker compose -f cookbook/postgres-memory/compose.yml down --volumes
```

The password and port are synthetic local-only values. Real deployments should use a secret
manager, TLS, a least-privilege database role, backups, retention policy, and network controls.
The adapter stores operational memory only; it grants no arbitrary SQL or remediation authority.

## Custom PostgreSQL schema

The checked `lumis.yml` deliberately uses an adopter-owned schema instead of `public`:

```yaml
spec:
  memory:
    provider: postgres
    connectionUrlEnv: LUMIS_MEMORY_DATABASE_URL
    schema: lumis_memory_cookbook
```

Validate the configuration offline, without resolving the secret or connecting to PostgreSQL:

```bash
uv run lumis doctor --config cookbook/postgres-memory/lumis.yml
```

Schema names must match the lowercase identifier contract and are validated before the adapter
quotes them. The plugin runs fixed migrations and statements inside that schema; it does not accept
arbitrary SQL or depend on the connection's default `search_path`. Separate applications can use
separate schemas and roles, but schema separation alone is not a tenancy boundary. Production
operators still own database grants, row-level policy where needed, TLS, rotation, backups,
retention, migration scheduling, and restore tests.
