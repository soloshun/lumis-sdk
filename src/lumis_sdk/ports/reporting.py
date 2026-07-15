"""Report-writer port."""

from pathlib import Path
from typing import Protocol

from lumis_sdk.domain import DiagnosisResult, IncidentInput


class ReportWriter(Protocol):
    """Persist one human-readable diagnosis report."""

    def write(
        self,
        *,
        incident: IncidentInput,
        diagnosis: DiagnosisResult,
        destination: Path,
    ) -> Path:
        """Write a report and return its resulting path."""
        ...
