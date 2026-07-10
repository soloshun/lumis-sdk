"""Cookbook-owned FastAPI simulator for one synthetic pipeline incident."""

from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="OpenARIA synthetic incident estate", version="0.1.0")

INCIDENT_ID = "schema-drift-001"
UNSEEN_INCIDENT_ID = "code-error-001"
PII_INCIDENT_ID = "pii-leak-001"

_INCIDENTS = {
    INCIDENT_ID: {
        "id": INCIDENT_ID,
        "source_tool": "synthetic_prefect",
        "pipeline_name": "stock_feature_pipeline",
        "environment": "demo",
        "status": "open",
    },
    UNSEEN_INCIDENT_ID: {
        "id": UNSEEN_INCIDENT_ID,
        "source_tool": "synthetic_prefect",
        "pipeline_name": "adjusted_price_pipeline",
        "environment": "demo",
        "status": "open",
    },
    PII_INCIDENT_ID: {
        "id": PII_INCIDENT_ID,
        "source_tool": "synthetic_prefect",
        "pipeline_name": "customer_ingestion_pipeline",
        "environment": "demo",
        "status": "open",
    },
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
    "verification": {"status": "not_run", "notes": "No remediation is available in this cookbook."},
}

_UNSEEN_CONTEXT = {
    "logs": ["calculate_price_adjustment failed with KeyError: 'adjusted_price'"],
    "metrics": {"failure_count": 1, "last_success_age_minutes": 60},
    "lineage": {"upstream": ["price_source"], "downstream": ["adjusted_price_dashboard"]},
    "schema": {"current": ["Date", "Close", "Volume"]},
    "verification": {"status": "not_run", "notes": "No remediation is available in this cookbook."},
}

_PII_CONTEXT = {
    "logs": [
        "customer sync failed after upstream response included "
        "customer_email=alex@example.com api_key=sk-abcdefghijklmnopqrstuvwxyz "
        "phone=415-555-2671 ssn=123-45-6789 card=4111 1111 1111 1111"
    ],
    "metrics": {"failure_count": 1, "last_success_age_minutes": 15},
    "lineage": {"upstream": ["crm_export"], "downstream": ["customer_warehouse"]},
    "schema": {"current": ["customer_id", "email", "status"]},
    "verification": {"status": "not_run", "notes": "No remediation is available in this cookbook."},
}

_CONTEXTS = {
    INCIDENT_ID: _CONTEXT,
    UNSEEN_INCIDENT_ID: _UNSEEN_CONTEXT,
    PII_INCIDENT_ID: _PII_CONTEXT,
}

_KNOWLEDGE_ROOT = Path(__file__).parent / "knowledge"
_CODE_ROOT = Path(__file__).parent / "synthetic_project"


def _require_incident(incident_id: str) -> None:
    if incident_id not in _INCIDENTS:
        raise HTTPException(status_code=404, detail="Synthetic incident not found")


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, object]:
    """Return the normalized synthetic incident."""
    _require_incident(incident_id)
    return _INCIDENTS[incident_id]


@app.get("/incidents/{incident_id}/context/{context_name}")
def get_context(incident_id: str, context_name: str) -> object:
    """Return one bounded synthetic context item for an agent tool."""
    _require_incident(incident_id)
    context = _CONTEXTS[incident_id]
    if context_name not in context:
        raise HTTPException(status_code=404, detail="Synthetic context item not found")
    return context[context_name]


@app.get("/code/{file_path:path}")
def read_code(file_path: str) -> dict[str, str]:
    """Return one safe, cookbook-owned synthetic source file."""
    candidate = (_CODE_ROOT / file_path).resolve()
    if _CODE_ROOT not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Synthetic code file not found")
    return {"path": file_path, "content": candidate.read_text(encoding="utf-8")}


@app.get("/knowledge/{knowledge_type}/{document_name}")
def read_knowledge(knowledge_type: str, document_name: str) -> dict[str, str]:
    """Return one cookbook-owned runbook or playbook Markdown document."""
    if knowledge_type not in {"runbooks", "playbooks"}:
        raise HTTPException(status_code=404, detail="Knowledge type not found")
    if Path(document_name).name != document_name:
        raise HTTPException(status_code=400, detail="Invalid knowledge document name")

    document_path = _KNOWLEDGE_ROOT / knowledge_type / f"{document_name}.md"
    if not document_path.is_file():
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    return {"name": document_name, "content": document_path.read_text(encoding="utf-8")}
