"""Offline Alertmanager normalization and Prometheus-evidence diagnosis walkthrough."""

from datetime import UTC, datetime
from pathlib import Path

from lumis_sdk.adapters.deterministic import diagnose_structured
from lumis_sdk.adapters.incidents import (
    InMemoryReplayGuard,
    WebhookConfig,
    normalize_webhook,
    sign_webhook_payload,
)
from lumis_sdk.config import load_diagnosis_rule
from lumis_sdk.domain import EvidenceItem

ROOT = Path(__file__).parent
NOW = datetime(2026, 7, 17, 8, 0, tzinfo=UTC)
SECRET = "synthetic-alertmanager-secret"


def main() -> None:
    """Authenticate a fixture and diagnose mapped provider-neutral fields."""
    body = (ROOT / "alertmanager.json").read_bytes()
    timestamp = int(NOW.timestamp())
    incident = normalize_webhook(
        body,
        {
            "X-Lumis-Delivery": "synthetic-alert-1",
            "X-Lumis-Timestamp": str(timestamp),
            "X-Lumis-Signature": sign_webhook_payload(body, timestamp=timestamp, secret=SECRET),
        },
        WebhookConfig(source_tool="alertmanager", secret_env="ALERTMANAGER_WEBHOOK_SECRET"),
        InMemoryReplayGuard(),
        environ={"ALERTMANAGER_WEBHOOK_SECRET": SECRET},
        now=NOW,
    )
    payload = incident.raw_payload
    alert = payload["alerts"][0]
    fields = {
        "alert": {"name": alert["labels"]["alertname"], "status": payload["status"]},
        "metric": {"failure_rate": 0.27},
        "pipeline": {"name": incident.pipeline_name},
    }
    evidence = EvidenceItem(
        id="prometheus-orders-failure-rate",
        source="prometheus-fixture",
        kind="prometheus_metric",
        detail="orders_etl_failure_rate=0.27 over the synthetic five-minute window",
        confidence=1.0,
        reference="fixture://prometheus/orders-etl-failure-rate",
    )
    result = diagnose_structured(fields, [load_diagnosis_rule(ROOT / "rule.yml")], [evidence])
    if result.winner is None:
        raise SystemExit("expected the synthetic Alertmanager rule to match")
    print(
        f"pipeline={incident.pipeline_name} rule={result.winner.rule_id} "
        f"classification={result.diagnosis.triage.classification} "
        f"evidence={result.diagnosis.evidence[0].id}"
    )


if __name__ == "__main__":
    main()
