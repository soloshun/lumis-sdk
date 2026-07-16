# Structured rule evaluation

This model-free cookbook demonstrates one portable `DiagnosisRule` against structured incident
fields and cited schema evidence.

```bash
uv run lumis rules test \
  --rule cookbook/structured-rule-evaluation/schema-change.yml \
  --input cookbook/structured-rule-evaluation/schema-change.json
```

Expected result:

- `matched` is `true`;
- the winner is `missing-required-column`;
- all scalar and quantified conditions are explained;
- the `dbt.model.orders` element index is retained in the quantified explanation;
- `schema://orders/current-vs-previous` is retained as an evidence reference.

The command only reads the two synthetic local files. It does not contact a model, telemetry
provider, database, orchestrator, or Lumis service, and it cannot execute remediation.
