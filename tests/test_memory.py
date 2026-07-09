"""Tests for local SQLite incident memory and transparent keyword search."""

from pathlib import Path

from openaria.incidents import incident_from_log
from openaria.memory import SQLiteIncidentStore, search_incidents
from openaria.reports import render_markdown_report
from openaria.triage import diagnose_log


def _save_schema_incident(database_path: Path) -> tuple[SQLiteIncidentStore, str]:
    log_text = "Pipeline: stock_feature_pipeline\nStep: transform_prices\nKeyError: 'Close'"
    incident = incident_from_log(log_text, "synthetic.log")
    diagnosis = diagnose_log(log_text)
    report = render_markdown_report(incident, diagnosis)
    store = SQLiteIncidentStore(database_path)
    stored = store.save(incident, diagnosis, report, Path("report.md"))
    return store, stored.id


def test_store_retrieves_and_resolves_an_incident(tmp_path: Path) -> None:
    """Saved incident details and a human resolution survive a database round trip."""
    store, incident_id = _save_schema_incident(tmp_path / "incidents.db")

    stored = store.get(incident_id)
    assert stored.incident.pipeline_name == "stock_feature_pipeline"
    assert stored.diagnosis.triage.classification == "schema_change"
    assert stored.resolution is None

    resolved = store.set_resolution(incident_id, "Updated the upstream field mapping.")
    assert resolved.resolution == "Updated the upstream field mapping."


def test_keyword_search_returns_scored_matching_incidents(tmp_path: Path) -> None:
    """Keyword retrieval returns the matching saved incident and its transparent score."""
    store, _ = _save_schema_incident(tmp_path / "incidents.db")

    results = search_incidents(store.list_all(), "KeyError Close")

    assert len(results) == 1
    assert results[0].score == 2
    assert results[0].incident.diagnosis.triage.classification == "schema_change"


def test_keyword_search_handles_empty_memory(tmp_path: Path) -> None:
    """Empty local memory is a valid search state."""
    store = SQLiteIncidentStore(tmp_path / "incidents.db")

    assert search_incidents(store.list_all(), "KeyError Close") == []
