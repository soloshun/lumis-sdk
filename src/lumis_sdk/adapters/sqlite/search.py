"""Transparent lexical retrieval over local SQLite incident records."""

import re
from dataclasses import dataclass

from .store import StoredIncident

_WORD_PATTERN = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True)
class SearchResult:
    """A matching incident and its inspectable lexical score."""

    incident: StoredIncident
    score: int


def search_incidents(incidents: list[StoredIncident], query: str) -> list[SearchResult]:
    """Rank incidents by the number of unique query terms they contain."""
    query_terms = set(_tokenize(query))
    if not query_terms:
        return []

    results: list[SearchResult] = []
    for incident in incidents:
        score = len(query_terms & set(_tokenize(_searchable_text(incident))))
        if score:
            results.append(SearchResult(incident=incident, score=score))
    return sorted(
        results, key=lambda result: (result.score, result.incident.created_at), reverse=True
    )


def _searchable_text(incident: StoredIncident) -> str:
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
    return _WORD_PATTERN.findall(value.lower())
