# Lumis SDK PostgreSQL memory

This independently installable package implements the public asynchronous `MemoryStore`
contract with PostgreSQL. It is optional: installing `lumis-sdk` does not install a PostgreSQL
driver.

Project YAML references an environment variable rather than containing credentials:

```yaml
spec:
  memory:
    provider: postgres
    connectionUrlEnv: LUMIS_MEMORY_DATABASE_URL
    schema: lumis_memory
```

The plugin requests `network` and `secrets` authority. Discovery grants neither authority;
applications must explicitly load the plugin and supply the referenced environment.

The store creates only its validated schema and tables, serializes migrations with a PostgreSQL
advisory transaction lock, treats `incident_id` as an idempotency key, bounds search candidates,
and never exposes arbitrary SQL or action execution.
