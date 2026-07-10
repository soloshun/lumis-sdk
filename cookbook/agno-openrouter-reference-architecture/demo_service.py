"""Cookbook-owned FastAPI simulator for one synthetic pipeline incident."""

from fastapi import FastAPI, HTTPException

app = FastAPI(title="OpenARIA synthetic incident estate", version="0.1.0")

INCIDENT_ID = "schema-drift-001"

_INCIDENT = {
    "id": INCIDENT_ID,
    "source_tool": "synthetic_prefect",
    "pipeline_name": "stock_feature_pipeline",
    "environment": "demo",
    "status": "open",
}

_CONTEXT = {
    "logs": ["transform_prices failed with KeyError: 'Close'"],
    "metrics": {"failure_count": 1, "last_success_age_minutes": 1440},
    "lineage": {
        "upstream": ["yfinance_extract"],
        "downstream": ["moving_average_features", "daily_stock_dashboard"],
    },
    "schema": {
        "expected": ["Date", "Open", "High", "Low", "Close", "Volume"],
        "current": ["Date", "Open", "High", "Low", "closing_price", "Volume"],
    },
    "runbook": "Compare the current schema with the last successful run before changing a mapping.",
    "playbook": "schema_mismatch_in_dataframe is recommendation-only and requires approval.",
    "verification": {"status": "not_run", "notes": "No remediation is available in this cookbook."},
}


def _require_incident(incident_id: str) -> None:
    if incident_id != INCIDENT_ID:
        raise HTTPException(status_code=404, detail="Synthetic incident not found")


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, object]:
    """Return the normalized synthetic incident."""
    _require_incident(incident_id)
    return _INCIDENT


@app.get("/incidents/{incident_id}/context/{context_name}")
def get_context(incident_id: str, context_name: str) -> object:
    """Return one bounded synthetic context item for an agent tool."""
    _require_incident(incident_id)
    if context_name not in _CONTEXT:
        raise HTTPException(status_code=404, detail="Synthetic context item not found")
    return _CONTEXT[context_name]
