"""Reference SQLite audit sink and explicitly separate human resolution attestations."""

import sqlite3
from pathlib import Path
from typing import Protocol

from lumis_sdk.investigation.contracts import HumanResolution, IncidentReport


class IncidentRecorder(Protocol):
    """Applications may implement their own database adapter without coupling it to the agent."""

    def save(self, report: IncidentReport) -> None: ...
    def record_resolution(self, resolution: HumanResolution) -> None: ...


class IncidentStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS incident_reports (
                    incident_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS incident_evidence (
                    incident_id TEXT NOT NULL, evidence_id TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY (incident_id, evidence_id));
                CREATE TABLE IF NOT EXISTS incident_receipts (
                    incident_id TEXT NOT NULL, receipt_id TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY (incident_id, receipt_id));
                CREATE TABLE IF NOT EXISTS human_resolutions (
                    id TEXT PRIMARY KEY, incident_id TEXT NOT NULL, payload TEXT NOT NULL);
            """)

    def save(self, report: IncidentReport) -> None:
        validated = IncidentReport.model_validate(report.model_dump())
        incident_id = validated.context.incident.id
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO incident_reports VALUES (?, ?)",
                (incident_id, validated.model_dump_json()),
            )
            connection.executemany(
                "INSERT INTO incident_evidence VALUES (?, ?, ?)",
                (
                    (incident_id, item.id, item.model_dump_json())
                    for item in validated.context.evidence
                ),
            )
            connection.executemany(
                "INSERT INTO incident_receipts VALUES (?, ?, ?)",
                ((incident_id, item.id, item.model_dump_json()) for item in validated.receipts),
            )

    def get(self, incident_id: str) -> IncidentReport | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload FROM incident_reports WHERE incident_id = ?", (incident_id,)
            ).fetchone()
        return IncidentReport.model_validate_json(row[0]) if row else None

    def record_resolution(self, resolution: HumanResolution) -> None:
        validated = HumanResolution.model_validate(resolution.model_dump())
        with sqlite3.connect(self.path) as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM incident_reports WHERE incident_id = ?", (validated.incident_id,)
                ).fetchone()
                is None
            ):
                raise ValueError("manual resolution requires an existing incident report")
            connection.execute(
                "INSERT INTO human_resolutions VALUES (?, ?, ?)",
                (validated.id, validated.incident_id, validated.model_dump_json()),
            )

    def resolutions(self, incident_id: str) -> tuple[HumanResolution, ...]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                "SELECT payload FROM human_resolutions WHERE incident_id = ? ORDER BY id",
                (incident_id,),
            ).fetchall()
        return tuple(HumanResolution.model_validate_json(row[0]) for row in rows)
