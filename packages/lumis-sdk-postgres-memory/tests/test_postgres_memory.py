"""Contract and integration tests for the optional PostgreSQL memory plugin."""

import asyncio
import os
from uuid import uuid4

import pytest
from lumis_postgres_memory import MANIFEST, PostgresMemoryPlugin, PostgresMemoryStore, create_plugin

from lumis_sdk.config import PostgresMemoryConfig
from lumis_sdk.domain import PluginAuthority, PluginCapability
from lumis_sdk.testkit import assert_memory_store_contract, assert_plugin_factory_contract


def test_manifest_declares_optional_memory_authorities() -> None:
    assert MANIFEST.spec.capabilities == [PluginCapability.MEMORY_STORE]
    assert MANIFEST.spec.required_authorities == [
        PluginAuthority.NETWORK,
        PluginAuthority.SECRETS,
    ]
    assert isinstance(
        assert_plugin_factory_contract(create_plugin, MANIFEST),
        PostgresMemoryPlugin,
    )


def test_plugin_resolves_only_the_named_environment_secret() -> None:
    config = PostgresMemoryConfig(
        provider="postgres",
        connectionUrlEnv="TEST_DATABASE_URL",
        schema="fixture_memory",
    )
    plugin = PostgresMemoryPlugin()

    store = plugin.create(
        config,
        environ={"TEST_DATABASE_URL": "postgresql://user:secret@localhost/database"},
    )

    assert store.schema_name == "fixture_memory"
    with pytest.raises(ValueError, match="is not set"):
        plugin.create(config, environ={})


@pytest.mark.skipif(
    "LUMIS_TEST_POSTGRES_URL" not in os.environ,
    reason="set LUMIS_TEST_POSTGRES_URL to run the PostgreSQL contract",
)
def test_postgres_store_satisfies_public_memory_contract() -> None:
    schema = f"lumis_test_{uuid4().hex}"
    store = PostgresMemoryStore(
        os.environ["LUMIS_TEST_POSTGRES_URL"],
        schema_name=schema,
    )

    asyncio.run(assert_memory_store_contract(store))
