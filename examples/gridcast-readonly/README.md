# GridCast read-only contract replay

Synthetic, offline example of external topology/observations. No GridCast application modules,
paid model, cluster, action executor or ground-truth label enters the runtime.

```bash
uv sync --all-groups
uv run lumis investigate \
  --project examples/gridcast-readonly/project.yaml \
  --incident examples/gridcast-readonly/incident.json \
  --observations examples/gridcast-readonly/observations.json
```

Expected: three hypotheses, one supported (possible deployment-driven query amplification), two
contradicted, four audited queries and `truth_state: unconfirmed_hypothesis`.
The example checks contracts, not scientific root-cause identification accuracy.

Omit `--observations` to withhold facts: expect `outcome: abstained`, missing checks and query
budget stop. Add `--generation-only` for initial observations plus candidate generation only.
Add `--store .lumis/gridcast.sqlite` to retain the result; repeated incident IDs are rejected.

[Live handoff](../../docs/operational-intelligence/gridcast-integration.md) explains namespace
discovery, OTLP, Prometheus and explicit optional model use. Full estate/cookbook work belongs in
the separately developed GridCast repository.
