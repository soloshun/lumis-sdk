"""Convert local inputs into vendor-neutral incident records."""

import re

from openaria.schemas import IncidentInput

_PIPELINE_PATTERN = re.compile(r"Pipeline:\s*(?P<pipeline>[\w.-]+)", re.IGNORECASE)


def incident_from_log(log_text: str, source_path: str) -> IncidentInput:
    """Normalize a manually supplied log into an incident input."""
    pipeline_match = _PIPELINE_PATTERN.search(log_text)
    pipeline_name = pipeline_match.group("pipeline") if pipeline_match else None

    return IncidentInput(
        source_tool="manual_log",
        pipeline_name=pipeline_name,
        raw_payload={"log": log_text, "source_path": source_path},
    )
