"""Read-only scalar SQL observations (PostgreSQL via the optional `sql` extra)."""

import math
import os
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

from lumis_sdk.connectors.settings import SqlQuery, SqlSource
from lumis_sdk.core import Evidence, EvidenceQuery, Incident
from lumis_sdk.security.redaction import redact_text

Connect = Callable[..., Awaitable[Any]]


async def _psycopg_connect(dsn: str, **kwargs: Any) -> Any:
    from psycopg import AsyncConnection

    return await AsyncConnection.connect(dsn, **kwargs)


class SqlConnector:
    """One short read-only transaction per registered query; no writes, DDL or session state."""

    def __init__(self, source: SqlSource, *, connect: Connect = _psycopg_connect) -> None:
        if not source.enabled or source.dsn_env is None:
            raise ValueError("enabled configured SQL source required")
        self.source = source
        self.connect = connect
        self.requests = 0

    async def collect(self, query: EvidenceQuery, incident: Incident) -> tuple[Evidence, ...]:
        parameters = SqlQuery.model_validate(query.parameters)
        if self.requests >= self.source.max_requests:
            raise ValueError("source request budget exhausted")
        self.requests += 1
        assert self.source.dsn_env is not None
        dsn = os.environ.get(self.source.dsn_env, "")
        if not dsn:
            raise ValueError("configured SQL connection string unavailable")
        connection = await self.connect(
            dsn,
            autocommit=False,
            connect_timeout=self.source.connect_timeout_seconds,
            options=(
                "-c default_transaction_read_only=on "
                f"-c statement_timeout={self.source.statement_timeout_ms}"
            ),
        )
        try:
            await connection.set_read_only(True)
            async with connection.cursor() as cursor:
                await cursor.execute(
                    parameters.sql,
                    {"started_at": incident.started_at, "ended_at": incident.ended_at},
                )
                rows = await cursor.fetchmany(2)
            await connection.rollback()
        finally:
            await connection.close()
        if len(rows) != 1 or len(rows[0]) != 1:
            raise ValueError("SQL query must return exactly one row with one column")
        value = rows[0][0]
        if value is None:
            return ()  # no value is no observation, never a zero
        if isinstance(value, Decimal):
            value = float(value)
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("invalid numeric observation")
        if not isinstance(value, bool | int | float | str):
            raise ValueError("SQL observation must be a number, boolean or text")
        if isinstance(value, str):
            value = redact_text(value)
            if len(value) > 4000:
                raise ValueError("observation exceeds text bound")
        return (
            Evidence(
                id=f"sql:{query.id}",
                query_id=query.id,
                entity_id=query.entity_id,
                key=query.key,
                value=value,
                # Evaluated over the incident window, which ends at `ended_at`.
                observed_at=incident.ended_at,
                source="sql",
                retrieval_method="SQL read-only transaction",
            ),
        )
