# Operational memory API

`lumis_sdk.ports.MemoryStore` is the provider-neutral asynchronous contract for retained incident
episodes, explicit confirmed resolutions, and transparent bounded retrieval.

```python
from pathlib import Path

from lumis_sdk.adapters.sqlite import SQLiteMemoryStore
from lumis_sdk.testkit import assert_memory_store_contract

store = SQLiteMemoryStore(Path(".lumis/portable-memory.db"))
await assert_memory_store_contract(store)
```

The contract uses `incident_id` as an idempotency key. Repeating identical content is safe;
different content for the same key raises `MemoryConflictError`. A resolution must target a saved
episode and remains an explicit `ConfirmedResolution`; model text never changes truth state.

## PostgreSQL plugin

Install the independent package alongside Lumis SDK `0.0.7` or another compatible core release:

```bash
pip install lumis-sdk-postgres-memory
```

```python
from lumis_postgres_memory import PostgresMemoryPlugin
from lumis_sdk.config import PostgresMemoryConfig

config = PostgresMemoryConfig(
    provider="postgres",
    connectionUrlEnv="LUMIS_MEMORY_DATABASE_URL",
    schema="lumis_memory",
)
store = PostgresMemoryPlugin().create(config)
```

The plugin requests network and secret authority and reads only the named environment variable.
Its migrations are serialized, schema identifiers are validated, candidate reads are bounded,
and search reasons use the same deterministic ranking contract as SQLite.

See [RFC 0002](../rfcs/0002-postgresql-memory.md) and the
[shared PostgreSQL cookbook](../../cookbook/postgres-memory/README.md).
