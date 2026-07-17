# Prometheus and Alertmanager walkthrough

This synthetic, offline example shows how an adopter can normalize an Alertmanager webhook and
supply bounded Prometheus metric evidence without adding Prometheus-specific logic to Lumis SDK
core. The adapter layer maps provider fields into a project-owned diagnosis contract.

```bash
uv run python cookbook/prometheus-alertmanager/demo.py
```

Expected output:

```text
pipeline=orders-etl rule=orders-etl-failure-rate classification=data_pipeline_reliability evidence=prometheus-orders-failure-rate
```

The demo authenticates exact fixture bytes, claims one delivery ID, maps the alert name/status,
supplies one synthetic metric as typed evidence, and evaluates a stable v1 rule. It makes no
network call and requires no Prometheus server.

For production, an adopter must run the webhook behind TLS, use a durable shared replay guard,
retrieve metrics through an allowlisted/time-bounded adapter, validate labels and tenancy, redact
sensitive values, enforce rate limits, and record retention. A firing alert and threshold breach
support a diagnosis; they do not confirm root cause or authorize remediation.
