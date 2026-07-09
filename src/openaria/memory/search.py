"""Transparent keyword search over local incident memory."""

import re
from dataclasses import dataclass

from openaria.memory.sqlite_store import StoredIncident

_WORD_PATTERN = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True)
class SearchResult:
    """A matching incident and the simple score used to rank it."""

    incident: StoredIncident
    score: int


def search_incidents(incidents: list[StoredIncident], query: str) -> list[SearchResult]:
    """Rank incidents by the number of unique query words they contain.

    This intentionally simple, inspectable algorithm is the Sprint 2 baseline;
    embeddings and vector retrieval are explicitly out of scope.
    """
    query_terms = set(_tokenize(query))
    if not query_terms:
        return []

    results: list[SearchResult] = []
    for incident in incidents:
        searchable_terms = set(_tokenize(_searchable_text(incident)))
        score = len(query_terms & searchable_terms)
        if score:
            results.append(SearchResult(incident=incident, score=score))

    return sorted(
        results, key=lambda result: (result.score, result.incident.created_at), reverse=True
    )


def _searchable_text(incident: StoredIncident) -> str:
    """Collect only locally stored text used by the keyword matcher."""
    return " ".join(
        [
            incident.incident.source_tool,
            incident.incident.pipeline_name or "",
            incident.diagnosis.triage.classification,
            incident.diagnosis.triage.summary,
            incident.diagnosis.root_cause_hypothesis,
            incident.report_markdown,
            incident.resolution or "",
        ]
    )


def _tokenize(value: str) -> list[str]:
    """Normalize text into words for the transparent local matcher."""
    return _WORD_PATTERN.findall(value.lower())
