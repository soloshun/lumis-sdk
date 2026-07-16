"""Tests for local SQLite incident memory and transparent keyword search."""

import asyncio
from pathlib import Path

import pytest

from lumis_sdk.adapters.deterministic import diagnose_text
from lumis_sdk.adapters.incidents import incident_from_log
from lumis_sdk.adapters.reports import render_markdown_report
from lumis_sdk.adapters.sqlite import SQLiteIncidentStore, SQLiteMemoryStore, search_incidents
from lumis_sdk.config import DeterministicRule
from lumis_sdk.ports import MemoryConflictError, MemoryQuery
from lumis_sdk.testkit import (
    assert_memory_store_contract,
    make_test_episode,
    make_test_resolution,
)


def _save_schema_incident(database_path: Path) -> tuple[SQLiteIncidentStore, str]:
    log_text = "INCIDENT_SIGNATURE"
    rule = DeterministicRule(
        id="fixture-rule",
        name="fixture-rule",
        all_contains=["INCIDENT_SIGNATURE"],
        classification="configured_failure",
        severity="medium",
        summary="A fixture signature appeared.",
        root_cause_hypothesis="The fixture rule matched.",
        confidence=0.6,
    )
    incident = incident_from_log(log_text, "synthetic.log", "fixture-project")
    diagnosis = diagnose_text(log_text, [rule])
    report = render_markdown_report(incident, diagnosis)
    store = SQLiteIncidentStore(database_path)
    stored = store.save(incident, diagnosis, report, Path("report.md"))
    return store, stored.id


def test_store_retrieves_and_resolves_an_incident(tmp_path: Path) -> None:
    """Saved incident details and a human resolution survive a database round trip."""
    store, incident_id = _save_schema_incident(tmp_path / "incidents.db")

    stored = store.get(incident_id)
    assert stored.incident.pipeline_name == "fixture-project"
    assert stored.diagnosis.triage.classification == "configured_failure"
    assert stored.resolution is None

    resolved = store.set_resolution(incident_id, "Updated the upstream field mapping.")
    assert resolved.resolution == "Updated the upstream field mapping."


def test_keyword_search_returns_scored_matching_incidents(tmp_path: Path) -> None:
    """Keyword retrieval returns the matching saved incident and its transparent score."""
    store, _ = _save_schema_incident(tmp_path / "incidents.db")

    results = search_incidents(store.list_all(), "INCIDENT_SIGNATURE")

    assert len(results) == 1
    assert results[0].score == 1
    assert results[0].incident.diagnosis.triage.classification == "configured_failure"


def test_keyword_search_handles_empty_memory(tmp_path: Path) -> None:
    """Empty local memory is a valid search state."""
    store = SQLiteIncidentStore(tmp_path / "incidents.db")

    assert search_incidents(store.list_all(), "INCIDENT_SIGNATURE") == []


def test_async_sqlite_store_satisfies_public_memory_contract(tmp_path: Path) -> None:
    """The reusable contract suite validates the SQLite MemoryStore implementation."""
    asyncio.run(assert_memory_store_contract(SQLiteMemoryStore(tmp_path / "portable-memory.db")))


def test_async_sqlite_store_is_idempotent_across_instances(tmp_path: Path) -> None:
    """Two process-like adapter instances can safely repeat one episode write."""
    database_path = tmp_path / "shared.db"
    episode = make_test_episode()

    async def exercise() -> None:
        first = SQLiteMemoryStore(database_path)
        second = SQLiteMemoryStore(database_path)
        await first.save_incident(episode)
        await second.save_incident(episode)
        await first.record_resolution(make_test_resolution())
        await second.save_incident(episode)
        matches = await second.search(MemoryQuery(text="fixture pipeline recovered"))
        assert matches[0].episode.resolution is not None

    asyncio.run(exercise())


def test_async_sqlite_store_rejects_conflicting_resolution(tmp_path: Path) -> None:
    """One incident ID cannot silently acquire two different confirmed outcomes."""
    store = SQLiteMemoryStore(tmp_path / "portable-memory.db")

    async def exercise() -> None:
        await store.save_incident(make_test_episode())
        resolution = make_test_resolution()
        await store.record_resolution(resolution)
        with pytest.raises(MemoryConflictError, match="different resolution"):
            await store.record_resolution(
                resolution.model_copy(update={"outcome": "A conflicting outcome."})
            )

    asyncio.run(exercise())
