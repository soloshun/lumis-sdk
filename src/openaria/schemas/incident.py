"""Incident input models."""

from typing import Any

from pydantic import BaseModel, Field


class IncidentInput(BaseModel):
    """A vendor-neutral representation of a received incident."""

    source_tool: str
    pipeline_name: str | None = None
    environment: str = "local"
    raw_payload: dict[str, Any] = Field(default_factory=dict)
