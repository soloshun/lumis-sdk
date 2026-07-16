"""Reusable assertions for third-party adapter contract tests."""

from lumis_sdk.adapters.reports import parse_json_report, render_json_report
from lumis_sdk.domain import (
    DiagnosisReportDocument,
    EvidenceCollection,
    EvidenceRequest,
)


def assert_evidence_collection_contract(
    collection: EvidenceCollection,
    request: EvidenceRequest,
) -> None:
    """Raise an actionable assertion when a provider violates public bounds."""
    if len(collection.items) > request.max_items:
        raise AssertionError("evidence provider returned more items than requested")
    ids = [item.id for item in collection.items]
    if len(ids) != len(set(ids)):
        raise AssertionError("evidence provider returned duplicate evidence IDs")
    if request.kinds and any(item.kind not in request.kinds for item in collection.items):
        raise AssertionError("evidence provider returned an unrequested evidence kind")
    if any(len(item.detail) > request.max_item_characters for item in collection.items):
        raise AssertionError("evidence provider returned an item above the character limit")
    total = sum(len(item.detail) for item in collection.items)
    if total > request.max_total_characters:
        raise AssertionError("evidence provider returned evidence above the total character limit")
    if any(failure.provider != collection.provider for failure in collection.failures):
        raise AssertionError("evidence failure provider does not match the collection provider")


def assert_json_report_round_trip(value: str) -> DiagnosisReportDocument:
    """Validate a JSON report and prove canonical serialization round-trips."""
    document = parse_json_report(value)
    canonical = render_json_report(
        document.incident,
        document.diagnosis,
        truth_state=document.truth_state,
        confirmed_resolution=document.confirmed_resolution,
    )
    if parse_json_report(canonical) != document:
        raise AssertionError("diagnosis report did not survive a canonical JSON round trip")
    return document
