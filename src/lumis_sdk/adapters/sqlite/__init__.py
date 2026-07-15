"""SQLite reference adapters."""

from .search import SearchResult, search_incidents
from .store import IncidentNotFoundError, SQLiteIncidentStore, StoredIncident

__all__ = [
    "IncidentNotFoundError",
    "SQLiteIncidentStore",
    "SearchResult",
    "StoredIncident",
    "search_incidents",
]
