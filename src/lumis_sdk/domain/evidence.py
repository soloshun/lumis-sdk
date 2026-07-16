"""Provider-neutral evidence collection contracts."""

from pydantic import Field

from .models import DomainModel, EvidenceItem, IncidentInput


class EvidenceRequest(DomainModel):
    """A bounded request for evidence related to one incident."""

    incident: IncidentInput
    kinds: list[str] = Field(default_factory=list)
    max_items: int = Field(default=25, ge=1, le=100)
    max_total_characters: int = Field(default=131_072, ge=1, le=1_000_000)
    max_item_characters: int = Field(default=8_000, ge=1, le=100_000)
    redact: bool = True


class EvidenceFailure(DomainModel):
    """A safe, structured collection failure that can be surfaced to adopters."""

    provider: str
    code: str
    message: str
    retryable: bool = False


class EvidenceCollection(DomainModel):
    """Evidence and explicit collection failures returned by one provider."""

    provider: str
    items: list[EvidenceItem] = Field(default_factory=list)
    failures: list[EvidenceFailure] = Field(default_factory=list)
    truncated: bool = False
