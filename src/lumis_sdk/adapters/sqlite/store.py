"""SQLite reference adapter for local incident memory."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from lumis_sdk.domain import DiagnosisResult, IncidentInput, TruthState


class IncidentNotFoundError(Exception):
    """Raised when an incident ID does not exist in local memory."""


@dataclass(frozen=True)
class StoredIncident:
    """An incident and diagnosis retained in local memory."""

    id: str
    created_at: datetime
    incident: IncidentInput
    diagnosis: DiagnosisResult
    report_markdown: str
    report_path: str
    resolution: str | None

    @property
    def truth_state(self) -> TruthState:
        """Expose whether memory is hypothesis-only or human-confirmed."""
        return (
            TruthState.HUMAN_CONFIRMED
            if self.resolution is not None
            else TruthState.UNCONFIRMED_HYPOTHESIS
        )


class SQLiteIncidentStore:
    """Persist Lumis SDK incidents in a local SQLite file."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def save(
        self,
        incident: IncidentInput,
        diagnosis: DiagnosisResult,
        report_markdown: str,
        report_path: Path,
    ) -> StoredIncident:
        """Create and persist a new local incident record."""
        stored = StoredIncident(
            id=str(uuid4()),
            created_at=datetime.now(UTC),
            incident=incident,
            diagnosis=diagnosis,
            report_markdown=report_markdown,
            report_path=str(report_path),
            resolution=None,
        )
        self._initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO incidents (
                    id, created_at, incident_json, diagnosis_json, report_markdown,
                    report_path, resolution
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.id,
                    stored.created_at.isoformat(),
                    json.dumps(stored.incident.model_dump(mode="json")),
                    json.dumps(stored.diagnosis.model_dump(mode="json")),
                    stored.report_markdown,
                    stored.report_path,
                    stored.resolution,
                ),
            )
        return stored

    def get(self, incident_id: str) -> StoredIncident:
        """Return one incident or raise a useful error if it is absent."""
        self._initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM incidents WHERE id = ?", (incident_id,)
            ).fetchone()
        if row is None:
            raise IncidentNotFoundError(f"No incident found with ID: {incident_id}")
        return self._from_row(row)

    def list_all(self) -> list[StoredIncident]:
        """Return incidents from newest to oldest for local keyword search."""
        self._initialize()
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM incidents ORDER BY created_at DESC").fetchall()
        return [self._from_row(row) for row in rows]

    def set_resolution(self, incident_id: str, resolution: str) -> StoredIncident:
        """Record a human-supplied final resolution for a local incident."""
        self.get(incident_id)
        with self._connect() as connection:
            connection.execute(
                "UPDATE incidents SET resolution = ? WHERE id = ?", (resolution, incident_id)
            )
        return self.get(incident_id)

    def _initialize(self) -> None:
        """Create the local incident table when memory is first used."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    incident_json TEXT NOT NULL,
                    diagnosis_json TEXT NOT NULL,
                    report_markdown TEXT NOT NULL,
                    report_path TEXT NOT NULL,
                    resolution TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with mapping-style rows."""
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _from_row(row: sqlite3.Row) -> StoredIncident:
        """Validate a stored database row as current Lumis SDK models."""
        return StoredIncident(
            id=str(row["id"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            incident=IncidentInput.model_validate_json(str(row["incident_json"])),
            diagnosis=DiagnosisResult.model_validate_json(str(row["diagnosis_json"])),
            report_markdown=str(row["report_markdown"]),
            report_path=str(row["report_path"]),
            resolution=str(row["resolution"]) if row["resolution"] is not None else None,
        )
