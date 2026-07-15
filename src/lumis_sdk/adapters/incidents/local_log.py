"""Normalize a bounded local log into the Lumis SDK incident domain."""

from lumis_sdk.domain import IncidentInput


def incident_from_log(log_text: str, source_path: str, project_name: str) -> IncidentInput:
    """Create a vendor-neutral incident from caller-supplied local log text."""
    return IncidentInput(
        source_tool="local_log",
        pipeline_name=project_name,
        raw_payload={"log": log_text, "source_path": source_path},
    )
