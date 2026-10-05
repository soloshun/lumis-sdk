"""A tiny synthetic conformance input, not an application-specific cookbook."""

from typing import Any

from lumis_sdk.runtime.documents import json_document
from lumis_sdk.runtime.project import OperationalProject


def starter_documents() -> dict[str, str]:
    """Return validated starter files with no network sources, secrets or ground-truth label."""
    config: dict[str, Any] = {
        "api_version": "lumis.dev/operational-v1alpha1",
        "project": {"name": "my-estate", "environment": "local"},
        "policies": {"default_action_mode": "read_only"},
        "graph": {"entities": [{"id": "service:demo", "kind": "service", "name": "Demo service"}]},
        "queries": [
            {
                "id": "health",
                "provider": "snapshot",
                "entity_id": "service:demo",
                "key": "healthy",
                "description": "Was the service healthy during the incident?",
            }
        ],
        "rule_hypotheses": [
            {
                "id": "service-unavailable",
                "statement": "Service unavailability may explain the failure.",
                "causal_path": ["service:demo"],
                "evidence_needed": ["health"],
                "predictions": [
                    {
                        "entity_id": "service:demo",
                        "key": "healthy",
                        "operator": "eq",
                        "value": False,
                    }
                ],
                "falsifiers": [
                    {"entity_id": "service:demo", "key": "healthy", "operator": "eq", "value": True}
                ],
            }
        ],
        "budget": {"max_queries": 2},
    }
    config["checks"] = [
        {"id": "service-health", "terminal": False, "hypothesis": config["rule_hypotheses"][0]}
    ]
    OperationalProject.model_validate(config)
    incident = {
        "id": "demo-001",
        "affected_entities": ["service:demo"],
        "symptoms": ["Synthetic request failed."],
        "started_at": "2026-10-03T12:00:00Z",
        "ended_at": "2026-10-03T12:30:00Z",
    }
    observations = [
        {
            "id": "demo-health",
            "query_id": "health",
            "entity_id": "service:demo",
            "key": "healthy",
            "value": False,
            "observed_at": "2026-10-03T12:15:00Z",
            "source": "synthetic-local-observation",
            "retrieval_method": "snapshot-replay",
        }
    ]
    return {
        "lumis.yaml": json_document(config),
        "incident.json": json_document(incident),
        "observations.json": json_document(observations),
    }
