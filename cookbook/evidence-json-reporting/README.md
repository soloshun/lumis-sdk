# Evidence collection and JSON reporting

This model-free cookbook demonstrates the complete v0.2 evidence/reporting slice:

1. read a synthetic local failure log;
2. collect a bounded synthetic schema diff through the public evidence-provider contract;
3. redact a synthetic owner email;
4. match a structured rule that requires `schema_diff`;
5. write a strict versioned JSON diagnosis report;
6. store the incident in local SQLite memory.

Run:

```bash
uv run lumis doctor \
  --config cookbook/evidence-json-reporting/lumis/lumis.yml

uv run lumis diagnose \
  --config cookbook/evidence-json-reporting/lumis/lumis.yml
```

The report is written to:

```text
cookbook/evidence-json-reporting/.lumis/reports/incident-report.json
```

Expected classification: `schema_change`.

The cookbook uses synthetic local files only. It makes no network or model call, does not connect
to a production schema registry, and cannot execute a remediation action.
