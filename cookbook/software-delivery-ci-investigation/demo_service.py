"""Cookbook-owned FastAPI simulator for synthetic CI and infrastructure incidents."""

from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="OpenARIA synthetic software-delivery estate", version="0.1.0")

LOCKFILE_ID = "lockfile-ci-001"
WORKFLOW_ID = "workflow-permission-001"
INFRA_ID = "infra-resource-001"

_INCIDENTS = {
    LOCKFILE_ID: {
        "id": LOCKFILE_ID,
        "source_tool": "synthetic_github_actions",
        "pipeline_name": "checkout-service-ci",
        "environment": "demo",
        "status": "open",
    },
    WORKFLOW_ID: {
        "id": WORKFLOW_ID,
        "source_tool": "synthetic_github_actions",
        "pipeline_name": "checkout-service-ci",
        "environment": "demo",
        "status": "open",
    },
    INFRA_ID: {
        "id": INFRA_ID,
        "source_tool": "synthetic_terraform_validate",
        "pipeline_name": "checkout-service-infra",
        "environment": "demo",
        "status": "open",
    },
}

_CONTEXTS = {
    LOCKFILE_ID: {
        "logs": ["uv sync --locked failed: lockfile is out of date"],
        "metrics": {"failed_runs": 1, "last_success_age_minutes": 30},
        "lineage": {"upstream": ["pyproject.toml"], "downstream": ["test job"]},
        "verification": {"status": "not_run", "notes": "No CI rerun occurs in this cookbook."},
    },
    WORKFLOW_ID: {
        "logs": ["release job failed with 403: Resource not accessible by integration"],
        "metrics": {"failed_runs": 1, "last_success_age_minutes": 120},
        "lineage": {"upstream": ["release workflow"], "downstream": ["release artifact"]},
        "verification": {
            "status": "not_run",
            "notes": "No workflow permission changes occur here.",
        },
    },
    INFRA_ID: {
        "logs": [
            "terraform validate failed: Reference to undeclared resource aws_s3_bucket.artifacts"
        ],
        "metrics": {"failed_runs": 1, "last_success_age_minutes": 60},
        "lineage": {"upstream": ["infra/main.tf"], "downstream": ["staging plan"]},
        "verification": {
            "status": "not_run",
            "notes": "No infrastructure plan or apply occurs here.",
        },
    },
}

_INVESTIGATION_GUIDES = {
    LOCKFILE_ID: {
        "context_names": list(_CONTEXTS[LOCKFILE_ID]),
        "code_files": [],
        "runbooks": [],
        "playbooks": ["dependency_lockfile_refresh"],
        "note": "Known rule match; the deterministic report is sufficient for this scenario.",
    },
    WORKFLOW_ID: {
        "context_names": list(_CONTEXTS[WORKFLOW_ID]),
        "code_files": [".github/workflows/release.yml"],
        "runbooks": ["ci-permission-investigation"],
        "playbooks": [],
        "note": (
            "Unknown scenario; inspect the listed workflow and runbook before recommending review."
        ),
    },
    INFRA_ID: {
        "context_names": list(_CONTEXTS[INFRA_ID]),
        "code_files": ["infra/main.tf"],
        "runbooks": ["infrastructure-reference-investigation"],
        "playbooks": [],
        "note": (
            "Unknown scenario; inspect the listed Terraform file and runbook "
            "before recommending review."
        ),
    },
}

_KNOWLEDGE_ROOT = Path(__file__).parent / "knowledge"
_CODE_ROOT = Path(__file__).parent / "synthetic_project"


def _require_incident(incident_id: str) -> None:
    if incident_id not in _INCIDENTS:
        raise HTTPException(status_code=404, detail="Synthetic incident not found")


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, object]:
    """Return one normalized synthetic software-delivery incident."""
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


@app.get("/incidents/{incident_id}/guide")
def get_investigation_guide(incident_id: str) -> dict[str, object]:
    """Return the valid evidence identifiers for one synthetic incident."""
    _require_incident(incident_id)
    return _INVESTIGATION_GUIDES[incident_id]


@app.get("/code/{file_path:path}")
def read_code(file_path: str) -> dict[str, str]:
    """Return one safe, cookbook-owned workflow, source, or infrastructure file."""
    candidate = (_CODE_ROOT / file_path).resolve()
    if _CODE_ROOT not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Synthetic project file not found")
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
