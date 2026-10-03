"""Read-only scalar SQL evidence: query contract, transaction guards and value normalization."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from lumis_sdk.connectors.settings import SqlQuery, SqlSource
from lumis_sdk.connectors.sql import SqlConnector
from lumis_sdk.core import EvidenceQuery, Incident

END = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
INCIDENT = Incident(
    id="i",
    symptoms=("alias moved",),
    started_at=END - timedelta(minutes=10),
    ended_at=END,
    affected_entities=("service:db",),
)
SOURCE = SqlSource(enabled=True, dsn_env="LUMIS_TEST_SQL_DSN", statement_timeout_ms=1500)


def query(sql):
    return EvidenceQuery(
        id="alias-moves",
        provider="sql",
        entity_id="service:db",
        key="alias_moves",
        description="Production alias moves in the window",
        parameters={"sql": sql},
    )


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM ml.model_events",
        "SELECT 1; DROP TABLE ml.model_events",
        "SELECT %(password)s",
        "SELECT 'a%' ",
    ],
)
def test_sql_query_contract_refuses_writes_stacking_and_unknown_parameters(sql):
    with pytest.raises(ValueError):
        SqlQuery(sql=sql)


def test_sql_source_requires_environment_dsn():
    with pytest.raises(ValueError, match="dsn_env"):
        SqlSource(enabled=True)


class FakeConnection:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    async def set_read_only(self, value):
        self.calls.append(("read_only", value))

    def cursor(self):
        connection = self

        class Cursor:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def execute(self, sql, params):
                connection.calls.append(("execute", sql, params))

            async def fetchmany(self, size):
                return connection.rows[:size]

        return Cursor()

    async def rollback(self):
        self.calls.append(("rollback",))

    async def close(self):
        self.calls.append(("close",))


def collect(rows, monkeypatch, sql="SELECT count(*) FROM t WHERE at <= %(ended_at)s"):
    monkeypatch.setenv("LUMIS_TEST_SQL_DSN", "postgresql://reader@db/estate")
    connection, seen = FakeConnection(rows), {}

    async def connect(dsn, **kwargs):
        seen.update(kwargs, dsn=dsn)
        return connection

    facts = asyncio.run(SqlConnector(SOURCE, connect=connect).collect(query(sql), INCIDENT))
    return facts, connection.calls, seen


def test_sql_runs_one_read_only_transaction_bound_to_the_incident_window(monkeypatch):
    facts, calls, seen = collect([(Decimal("2"),)], monkeypatch)
    assert facts[0].value == 2.0 and facts[0].observed_at == INCIDENT.ended_at
    assert facts[0].source == "sql" and facts[0].query_id == "alias-moves"
    assert "default_transaction_read_only=on" in seen["options"]
    assert "statement_timeout=1500" in seen["options"] and seen["autocommit"] is False
    assert calls[0] == ("read_only", True)
    assert calls[1][2] == {"started_at": INCIDENT.started_at, "ended_at": INCIDENT.ended_at}
    assert calls[-2:] == [("rollback",), ("close",)]


def test_sql_null_is_no_observation_and_shapes_are_enforced(monkeypatch):
    assert collect([(None,)], monkeypatch)[0] == ()
    for rows in ([], [(1,), (2,)], [(1, 2)], [(float("nan"),)], [(b"raw",)]):
        with pytest.raises(ValueError):
            collect(rows, monkeypatch)


@pytest.mark.skipif(
    not os.environ.get("LUMIS_TEST_POSTGRES_DSN"), reason="explicit PostgreSQL DSN required"
)
def test_sql_against_postgres_is_read_only(monkeypatch):
    monkeypatch.setenv("LUMIS_TEST_SQL_DSN", os.environ["LUMIS_TEST_POSTGRES_DSN"])
    connector = SqlConnector(SOURCE)
    (fact,) = asyncio.run(
        connector.collect(query("SELECT extract(epoch FROM %(ended_at)s::timestamptz)"), INCIDENT)
    )
    assert fact.value == INCIDENT.ended_at.timestamp()
    writer = query("WITH moved AS (DELETE FROM pg_catalog.pg_class RETURNING 1) SELECT 1")
    with pytest.raises(Exception, match="read-only"):
        asyncio.run(SqlConnector(SOURCE).collect(writer, INCIDENT))


def test_project_registers_sql_queries_only_for_an_enabled_source():
    import json
    from pathlib import Path

    from lumis_sdk.runtime.project import OperationalProject
    from lumis_sdk.runtime.scaffold import starter_documents
    from lumis_sdk.runtime.session import local_connectors

    config = json.loads(starter_documents()["lumis.yaml"])
    entity = config["queries"][0]["entity_id"]
    config["queries"].append(query("SELECT count(*) FROM t").model_dump() | {"entity_id": entity})
    with pytest.raises(ValueError, match="enabled source"):
        OperationalProject.model_validate(config)
    config["sources"] = {"sql": {"enabled": True, "dsn_env": "ESTATE_READONLY_DSN"}}
    project = OperationalProject.model_validate(config)
    assert set(local_connectors(project, Path(), None)) == {"snapshot", "sql"}
    config["queries"][-1]["parameters"] = {"sql": "UPDATE t SET x = 1"}
    with pytest.raises(ValueError, match="SELECT"):
        OperationalProject.model_validate(config)
