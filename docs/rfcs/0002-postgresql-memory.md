# RFC 0002: Optional PostgreSQL operational memory

- Status: Accepted
- Target: v0.3
- Issues: #2, #32, #34, #35

## Decision

Lumis SDK keeps `sqlite` as its zero-dependency default and adds a strict `postgres` project
configuration that contains only a connection environment-variable reference and bounded
adapter settings. PostgreSQL implementation code and `psycopg` ship in the independently
installable `lumis-sdk-postgres-memory` package, discovered through the v0.3 plugin SDK.

Core publishes the asynchronous `MemoryStore` port, reusable contract assertions, deterministic
ranking helpers, and an asynchronous SQLite reference adapter. A plugin capability object may
compose a concrete store from `PostgresMemoryConfig` and an explicitly supplied environment.

## Configuration

```yaml
spec:
  memory:
    provider: postgres
    connectionUrlEnv: LUMIS_MEMORY_DATABASE_URL
    schema: lumis_memory
    connectTimeoutSeconds: 10
    maxSearchCandidates: 1000
```

`connectionUrlEnv` must be an environment-variable name. A URL, password, token, or generic
secret value is invalid in this field. Schema names are limited to lowercase PostgreSQL
identifiers and are always quoted through the driver.

## Persistence and truth

- `incident_id` is the episode idempotency key.
- Repeating the same episode or resolution is a no-op.
- Reusing an ID for different content raises `MemoryConflictError`.
- A resolution for an absent episode raises `MemoryIncidentNotFoundError`.
- `record_resolution` copies the explicit resolution truth state onto the retained episode.
- Model output never calls `record_resolution` automatically.
- Verification-confirmed, rejected, and superseded lifecycle policy remains v0.5 work; this RFC
  stores the explicit state supplied through the public contract and does not infer it.

## Migrations and concurrency

Each adapter owns a monotonically increasing schema version. PostgreSQL migrations run in a
transaction while holding a schema-specific advisory transaction lock. SQLite initialization
uses an immediate transaction. An adapter refuses a database whose schema version is newer than
it supports.

The PostgreSQL adapter owns one connection per public operation. This conservative lifecycle is
safe for CLI jobs and worker processes and avoids a hidden global pool. Applications that need
pooling may wrap or contribute an adapter while preserving the same contract and limits.

## Retrieval

`MemoryQuery.limit` remains bounded to 100. Adapters read at most `maxSearchCandidates`, then use
the shared deterministic lexical/filter ranking function. Every result includes a numeric score
and human-readable reasons. This is operational retrieval, not semantic truth or permission to
act.

## Security and authority

The plugin declares `memory_store`, `network`, and `secrets`. Discovery grants none of these
authorities. Applications must explicitly load it and provide the named environment mapping.
The adapter creates and accesses only its validated schema and fixed tables; it accepts no SQL
fragments and exposes no execution API.

Database transport security, credential rotation, network policy, backup, retention, and
least-privilege roles remain deployment responsibilities. Production roles should not own
unrelated schemas or have action-execution privileges.

## Compatibility

Existing project files that omit `memory.provider` continue to select SQLite. Existing
`SQLiteIncidentStore` CLI/report behavior remains available. The reference CLI continues to use
its report-aware SQLite store; applications select PostgreSQL through the public Python/plugin
composition API until report persistence is separated into its own port.

## Rejected alternatives

- Core PostgreSQL extra: still couples the main distribution lock and security surface to a
  database driver.
- Credentials directly in YAML: creates accidental source-control and report leakage.
- Arbitrary DSN/SQL plugin settings: weakens validation and grants unnecessary authority.
- Automatic promotion of diagnoses into confirmed memory: violates the paper's explicit
  verification and learning boundary.
