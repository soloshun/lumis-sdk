"""Evidence-provider port."""

from typing import Protocol

from lumis_sdk.domain import EvidenceCollection, EvidenceRequest


class EvidenceProvider(Protocol):
    """Collect bounded evidence without exposing provider SDK types."""

    name: str

    async def collect(self, request: EvidenceRequest) -> EvidenceCollection:
        """Return evidence and explicit failures for one incident."""
        ...
