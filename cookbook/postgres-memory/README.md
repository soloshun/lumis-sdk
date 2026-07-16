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
