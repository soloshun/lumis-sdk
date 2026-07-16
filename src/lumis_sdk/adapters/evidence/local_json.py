"""Bounded local JSON evidence provider."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from lumis_sdk.domain import (
    EvidenceCollection,
    EvidenceFailure,
    EvidenceItem,
    EvidenceRequest,
)

MAX_EVIDENCE_FILE_BYTES = 1_048_576


class LocalJsonEvidenceProvider:
    """Read synthetic or project-owned evidence from one bounded local JSON file."""

    name = "local-json"

    def __init__(
        self,
        path: Path,
        *,
        max_file_bytes: int = MAX_EVIDENCE_FILE_BYTES,
    ) -> None:
        self.path = path
        self.max_file_bytes = max_file_bytes

    async def collect(self, request: EvidenceRequest) -> EvidenceCollection:
        """Load evidence from the explicitly configured path without network access."""
        del request
        if not self.path.is_file():
            return self._failure("source_unavailable", "Evidence file is missing or not a file.")
        if self.path.stat().st_size > self.max_file_bytes:
            return self._failure(
                "source_too_large",
                f"Evidence file exceeds {self.max_file_bytes} bytes.",
            )
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            items_raw = _items_from_payload(raw)
            items = [EvidenceItem.model_validate(item) for item in items_raw]
        except (OSError, json.JSONDecodeError, ValidationError, ValueError):
            return self._failure(
                "invalid_payload",
                "Evidence file could not be parsed as a valid evidence collection.",
            )
        return EvidenceCollection(provider=self.name, items=items)

    def _failure(self, code: str, message: str) -> EvidenceCollection:
        return EvidenceCollection(
            provider=self.name,
            failures=[
                EvidenceFailure(
                    provider=self.name,
                    code=code,
                    message=message,
                )
            ],
        )


def _items_from_payload(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("items"), list):
        return list(raw["items"])
    raise ValueError("Expected an evidence array or an object containing an items array.")
