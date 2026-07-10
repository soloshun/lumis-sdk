"""Convert local inputs into vendor-neutral incident records."""

from openaria.schemas import IncidentInput


def incident_from_log(log_text: str, source_path: str, project_name: str) -> IncidentInput:
    """Normalize a manually supplied log into an incident input."""
    return IncidentInput(
        source_tool="manual_log",
        pipeline_name=project_name,
        raw_payload={"log": log_text, "source_path": source_path},
    )
