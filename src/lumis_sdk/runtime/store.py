"""Inspectable local persistence of investigations, including ordinary abstention outcomes."""

import sqlite3
from pathlib import Path

from lumis_sdk.core import Investigation


class InvestigationStore:
    """One local SQLite store. Environment/customer isolation is a caller-owned file boundary."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS investigations "
                "(incident_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

    def save(self, investigation: Investigation) -> None:
        """Retain a terminal record; duplicate incident IDs are rejected."""
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO investigations VALUES (?, ?)",
                (
                    investigation.context.incident.id,
                    investigation.model_dump_json(),
                ),
            )

    def get(self, incident_id: str) -> Investigation | None:
        """Read a schema-validated precedent without upgrading its truth state."""
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload FROM investigations WHERE incident_id = ?", (incident_id,)
            ).fetchone()
        return Investigation.model_validate_json(row[0]) if row else None
