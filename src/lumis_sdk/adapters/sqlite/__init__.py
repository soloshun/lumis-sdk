"""SQLite reference adapters."""

from .memory import SQLiteMemoryStore
from .search import SearchResult, search_incidents
from .store import IncidentNotFoundError, SQLiteIncidentStore, StoredIncident

__all__ = [
    "IncidentNotFoundError",
    "SQLiteIncidentStore",
    "SearchResult",
    "SQLiteMemoryStore",
    "StoredIncident",
    "search_incidents",
]
