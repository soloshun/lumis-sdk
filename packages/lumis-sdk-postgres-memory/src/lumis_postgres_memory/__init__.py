"""Optional PostgreSQL MemoryStore plugin for Lumis SDK."""

import asyncio
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql

from lumis_sdk.adapters.memory import is_idempotent_episode_replay, rank_memory_episodes
from lumis_sdk.config import PostgresMemoryConfig
from lumis_sdk.domain import ConfirmedResolution, PluginManifest
from lumis_sdk.ports import (
    IncidentEpisode,
    MemoryConflictError,
    MemoryIncidentNotFoundError,
    MemoryMatch,
    MemoryQuery,
)

_SCHEMA_VERSION = 1
_MANIFEST_PATHS = (
    Path(__file__).with_name("lumis-plugin.json"),
    Path(__file__).parents[1] / "lumis-plugin.json",
    Path(__file__).parents[2] / "lumis-plugin.json",
)
MANIFEST = PluginManifest.model_validate_json(
    next(path for path in _MANIFEST_PATHS if path.is_file()).read_text(encoding="utf-8")
)


class PostgresMemoryStore:
    """PostgreSQL implementation with per-operation connection ownership."""

    def __init__(
        self,
        connection_url: str,
        *,
        schema_name: str = "lumis_memory",
        connect_timeout_seconds: int = 10,
        max_search_candidates: int = 1_000,
    ) -> None:
        if not connection_url:
            raise ValueError("connection_url must not be empty")
        config = PostgresMemoryConfig(
            provider="postgres",
            connectionUrlEnv="VALIDATED_AT_COMPOSITION",
            schema=schema_name,
            connectTimeoutSeconds=connect_timeout_seconds,
            maxSearchCandidates=max_search_candidates,
        )
        self._connection_url = connection_url
        self.schema_name = config.schema_name
        self.connect_timeout_seconds = config.connect_timeout_seconds
        self.max_search_candidates = config.max_search_candidates

    @classmethod
    def from_environment(
        cls,
        config: PostgresMemoryConfig,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> "PostgresMemoryStore":
        """Resolve the configured secret reference without retaining the environment mapping."""
        values = os.environ if environ is None else environ
        connection_url = values.get(config.connection_url_env)
        if not connection_url:
            raise ValueError(
                f"Required PostgreSQL memory environment variable "
                f"{config.connection_url_env!r} is not set"
            )
        return cls(
            connection_url,
            schema_name=config.schema_name,
            connect_timeout_seconds=config.connect_timeout_seconds,
            max_search_candidates=config.max_search_candidates,
        )

    async def save_incident(self, incident: IncidentEpisode) -> None:
        """Store an episode idempotently by incident_id."""
        await asyncio.to_thread(self._save_incident, incident)

    async def record_resolution(self, resolution: ConfirmedResolution) -> None:
        """Attach one explicit confirmed resolution to an existing episode."""
        await asyncio.to_thread(self._record_resolution, resolution)

    async def search(self, query: MemoryQuery) -> list[MemoryMatch]:
        """Rank a bounded PostgreSQL candidate set with public deterministic reasons."""
        episodes = await asyncio.to_thread(self._load_candidates)
        return rank_memory_episodes(episodes, query)

    def _save_incident(self, incident: IncidentEpisode) -> None:
        self._initialize()
        payload = incident.model_dump_json()
        now = datetime.now(UTC)
        with self._connect() as connection:
            cursor = connection.execute(
                sql.SQL(
                    """
                    INSERT INTO {}.episodes (
                        incident_id, episode_json, created_at, updated_at
                    ) VALUES (%s, %s::jsonb, %s, %s)
                    ON CONFLICT(incident_id) DO NOTHING
                    """
                ).format(sql.Identifier(self.schema_name)),
                (incident.incident_id, payload, now, now),
            )
            if cursor.rowcount == 1:
                return
            existing = self._get_episode(connection, incident.incident_id)
        assert existing is not None
        if not is_idempotent_episode_replay(existing, incident):
            raise MemoryConflictError(
                f"incident_id {incident.incident_id!r} already stores different content"
            )

    def _record_resolution(self, resolution: ConfirmedResolution) -> None:
        self._initialize()
        incident_id = str(resolution.incident_id)
        with self._connect() as connection:
            existing = self._get_episode(connection, incident_id, required=False)
            if existing is None:
                raise MemoryIncidentNotFoundError(
                    f"No memory episode found for incident_id {incident_id!r}"
                )
            if existing.resolution is not None:
                if existing.resolution == resolution:
                    return
                raise MemoryConflictError(
                    f"incident_id {incident_id!r} already has a different resolution"
                )
            updated = existing.model_copy(
                update={
                    "resolution": resolution,
                    "truth_state": resolution.truth_state,
                }
            )
            connection.execute(
                sql.SQL(
                    """
                    UPDATE {}.episodes
                    SET episode_json = %s::jsonb, updated_at = %s
                    WHERE incident_id = %s
                    """
                ).format(sql.Identifier(self.schema_name)),
                (updated.model_dump_json(), datetime.now(UTC), incident_id),
            )

    def _load_candidates(self) -> list[IncidentEpisode]:
        self._initialize()
        with self._connect() as connection:
            rows = connection.execute(
                sql.SQL(
                    """
                    SELECT episode_json::text
                    FROM {}.episodes
                    ORDER BY updated_at DESC, incident_id DESC
                    LIMIT %s
                    """
                ).format(sql.Identifier(self.schema_name)),
                (self.max_search_candidates,),
            ).fetchall()
        return [IncidentEpisode.model_validate_json(str(row[0])) for row in rows]

    def _initialize(self) -> None:
        schema = sql.Identifier(self.schema_name)
        with self._connect() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"lumis-sdk-memory:{self.schema_name}",),
            )
            connection.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(schema))
            connection.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {}.schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL
                    )
                    """
                ).format(schema)
            )
            current = connection.execute(
                sql.SQL("SELECT MAX(version) FROM {}.schema_migrations").format(schema)
            ).fetchone()
            current_value = current[0] if current is not None else None
            if current_value is not None and not isinstance(current_value, int):
                raise RuntimeError("PostgreSQL returned a non-integer memory schema version")
            current_version = current_value or 0
            if current_version > _SCHEMA_VERSION:
                raise RuntimeError(
                    f"PostgreSQL memory schema {current_version} is newer than supported "
                    f"version {_SCHEMA_VERSION}"
                )
            connection.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {}.episodes (
                        incident_id TEXT PRIMARY KEY,
                        episode_json JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                ).format(schema)
            )
            if current_version < _SCHEMA_VERSION:
                connection.execute(
                    sql.SQL(
                        """
                        INSERT INTO {}.schema_migrations (version, applied_at)
                        VALUES (%s, %s)
                        ON CONFLICT(version) DO NOTHING
                        """
                    ).format(schema),
                    (_SCHEMA_VERSION, datetime.now(UTC)),
                )

    def _connect(self) -> psycopg.Connection[tuple[object, ...]]:
        return psycopg.connect(
            self._connection_url,
            connect_timeout=self.connect_timeout_seconds,
        )

    def _get_episode(
        self,
        connection: psycopg.Connection[tuple[object, ...]],
        incident_id: str,
        *,
        required: bool = True,
    ) -> IncidentEpisode | None:
        row = connection.execute(
            sql.SQL("SELECT episode_json::text FROM {}.episodes WHERE incident_id = %s").format(
                sql.Identifier(self.schema_name)
            ),
            (incident_id,),
        ).fetchone()
        if row is None:
            if required:
                raise MemoryIncidentNotFoundError(
                    f"No memory episode found for incident_id {incident_id!r}"
                )
            return None
        return IncidentEpisode.model_validate_json(str(row[0]))


@dataclass(frozen=True)
class PostgresMemoryPlugin:
    """Explicit composition surface returned by the plugin entry point."""

    name: str = "postgres-memory"

    def create(
        self,
        config: PostgresMemoryConfig,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> PostgresMemoryStore:
        return PostgresMemoryStore.from_environment(config, environ=environ)


class PostgresMemoryPluginFactory:
    """Callable plugin entry point carrying the validated runtime manifest."""

    lumis_manifest = MANIFEST

    def __call__(self) -> PostgresMemoryPlugin:
        return PostgresMemoryPlugin()


create_plugin = PostgresMemoryPluginFactory()

__all__ = [
    "MANIFEST",
    "PostgresMemoryPlugin",
    "PostgresMemoryStore",
    "create_plugin",
]
