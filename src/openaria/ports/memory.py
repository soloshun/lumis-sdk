"""Incident-memory port independent of SQLite, Postgres, or hosted products."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from openaria.domain import ConfirmedResolution, DiagnosisResult, IncidentInput, TruthState


class MemoryPortModel(BaseModel):
    """Strict base for memory contracts."""

    model_config = ConfigDict(extra="forbid")


class IncidentEpisode(MemoryPortModel):
    """Portable memory record with an explicit truth state."""

    incident_id: str
    incident: IncidentInput
    diagnosis: DiagnosisResult
    truth_state: TruthState = TruthState.UNCONFIRMED_HYPOTHESIS


class MemoryQuery(MemoryPortModel):
    """Transparent structured and lexical memory query."""

    text: str
    classification: str | None = None
    pipeline_name: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class MemoryMatch(MemoryPortModel):
    """A ranked memory result with human-readable scoring reasons."""

    episode: IncidentEpisode
    score: float = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)


class MemoryStore(Protocol):
    """Persist and retrieve incident knowledge behind a replaceable adapter."""

    async def save_incident(self, incident: IncidentEpisode) -> None:
        """Store one incident episode without changing its truth state."""
        ...

    async def record_resolution(self, resolution: ConfirmedResolution) -> None:
        """Record an explicitly confirmed resolution."""
        ...

    async def search(self, query: MemoryQuery) -> list[MemoryMatch]:
        """Return ranked matches with transparent reasons."""
        ...
