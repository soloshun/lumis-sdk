"""Cookbook-owned FastAPI simulator for synthetic regression-pipeline incidents."""

from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="OpenARIA synthetic ML regression estate", version="0.1.0")

FEATURE_DRIFT_ID = "feature-drift-001"
FEATURE_CONTRACT_ID = "feature-contract-001"
MODEL_REGRESSION_ID = "model-regression-001"

_INCIDENTS = {
    FEATURE_DRIFT_ID: {
        "id": FEATURE_DRIFT_ID,
        "source_tool": "synthetic_ml_monitor",
        "pipeline_name": "housing_price_regression",
        "environment": "demo",
        "status": "open",
    },
    FEATURE_CONTRACT_ID: {
        "id": FEATURE_CONTRACT_ID,
        "source_tool": "synthetic_model_service",
        "pipeline_name": "housing_price_regression",
        "environment": "demo",
        "status": "open",
    },
    MODEL_REGRESSION_ID: {
        "id": MODEL_REGRESSION_ID,
        "source_tool": "synthetic_ml_monitor",
        "pipeline_name": "housing_price_regression",
        "environment": "demo",
        "status": "open",
    },
}

_CONTEXTS = {
    FEATURE_DRIFT_ID: {
        "logs": ["income z_score=4.2 exceeded threshold=3.0 during feature monitoring"],
        "metrics": {"income_z_score": 4.2, "drift_threshold": 3.0, "baseline_rmse": 5.1},
        "lineage": {"upstream": ["customer_profile_export"], "downstream": ["housing_regressor"]},
        "schema": {"expected_features": ["rooms", "area_sq_m", "income"]},
        "verification": {"status": "not_run", "notes": "No retraining or deployment runs here."},
    },
    FEATURE_CONTRACT_ID: {
        "logs": ["predict failed with ValueError: expected 3 features but received 2"],
        "metrics": {"prediction_failure_count": 18, "last_success_age_minutes": 20},
        "lineage": {"upstream": ["listing_api"], "downstream": ["housing_prediction_api"]},
        "schema": {
            "request_features": ["rooms", "area_sq_m"],
            "model_features": ["rooms", "area_sq_m", "income"],
        },
        "verification": {"status": "not_run", "notes": "No interface change runs here."},
    },
    MODEL_REGRESSION_ID: {
        "logs": ["validation RMSE=12.8 exceeded threshold=8.0 after candidate retraining"],
        "metrics": {"baseline_rmse": 5.1, "candidate_rmse": 12.8, "acceptance_threshold": 8.0},
        "lineage": {"upstream": ["housing_train.csv"], "downstream": ["candidate_model_registry"]},
        "schema": {"training_features": ["rooms", "area_sq_m", "income"]},
        "verification": {"status": "not_run", "notes": "The candidate model was not promoted."},
    },
}

_KNOWLEDGE_ROOT = Path(__file__).parent / "knowledge"
_CODE_ROOT = Path(__file__).parent / "synthetic_project"


def _require_incident(incident_id: str) -> None:
    if incident_id not in _INCIDENTS:
        raise HTTPException(status_code=404, detail="Synthetic incident not found")


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, object]:
    """Return one normalized synthetic ML incident."""
    _require_incident(incident_id)
    return _INCIDENTS[incident_id]


@app.get("/incidents/{incident_id}/context/{context_name}")
def get_context(incident_id: str, context_name: str) -> object:
    """Return one bounded synthetic context item."""
    _require_incident(incident_id)
    context = _CONTEXTS[incident_id]
    if context_name not in context:
        raise HTTPException(status_code=404, detail="Synthetic context item not found")
    return context[context_name]


@app.get("/code/{file_path:path}")
def read_code(file_path: str) -> dict[str, str]:
    """Return one safe, cookbook-owned source or data file."""
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
