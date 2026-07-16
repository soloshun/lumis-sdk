"""Contract tests for bounded provider-neutral evidence collection."""

import asyncio
import json
from pathlib import Path

from lumis_sdk.adapters.evidence import LocalJsonEvidenceProvider
from lumis_sdk.application import EvidenceService
from lumis_sdk.domain import EvidenceCollection, EvidenceItem, EvidenceRequest
from lumis_sdk.testkit import (
    FakeEvidenceProvider,
    assert_evidence_collection_contract,
    make_test_evidence,
    make_test_incident,
)


def test_evidence_service_redacts_deduplicates_filters_and_bounds() -> None:
    """Application orchestration enforces public safety bounds over provider output."""
    provider = FakeEvidenceProvider(
        EvidenceCollection(
            provider="ignored",
            items=[
                EvidenceItem(
                    id="one",
                    source="fixture",
                    kind="log_window",
                    detail="api_key=unsafe " + "x" * 100,
                    confidence=1.0,
                    reference="https://person@example.com/log",
                    attributes={"owner": "person@example.com"},
                ),
                make_test_evidence(evidence_id="one"),
                make_test_evidence(evidence_id="schema", kind="schema_diff"),
            ],
        )
    )
    request = EvidenceRequest(
        incident=make_test_incident(),
        kinds=["log_window"],
        max_items=2,
        max_item_characters=40,
        max_total_characters=80,
    )

    collection = asyncio.run(EvidenceService(provider).collect(request))

    assert provider.calls == 1
    assert collection.provider == "fake-evidence"
    assert collection.truncated is True
    assert len(collection.items) == 1
    assert "unsafe" not in collection.items[0].detail
    assert "person@example.com" not in (collection.items[0].reference or "")
    assert collection.items[0].attributes["owner"] == "[REDACTED_EMAIL]"
    assert_evidence_collection_contract(collection, request)


def test_local_json_provider_returns_items_and_structured_failures(tmp_path: Path) -> None:
    """The reference adapter reads one bounded local file and fails safely."""
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(
        json.dumps({"items": [make_test_evidence().model_dump(mode="json")]}),
        encoding="utf-8",
    )
    request = EvidenceRequest(incident=make_test_incident())

    valid = asyncio.run(LocalJsonEvidenceProvider(evidence_path).collect(request))
    missing = asyncio.run(LocalJsonEvidenceProvider(tmp_path / "missing.json").collect(request))
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{", encoding="utf-8")
    invalid = asyncio.run(LocalJsonEvidenceProvider(invalid_path).collect(request))

    assert valid.items[0].reference == "testkit://evidence/test-evidence-1"
    assert missing.failures[0].code == "source_unavailable"
    assert invalid.failures[0].code == "invalid_payload"


class SlowEvidenceProvider:
    name = "slow"

    async def collect(self, request: EvidenceRequest) -> EvidenceCollection:
        del request
        await asyncio.sleep(0.05)
        return EvidenceCollection(provider=self.name)


def test_evidence_timeout_is_an_explicit_retryable_failure() -> None:
    """A provider timeout never becomes an empty successful collection."""
    collection = asyncio.run(
        EvidenceService(SlowEvidenceProvider(), timeout_seconds=0.001).collect(
            EvidenceRequest(incident=make_test_incident())
        )
    )

    assert collection.items == []
    assert collection.failures[0].code == "timeout"
    assert collection.failures[0].retryable is True
