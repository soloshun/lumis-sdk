"""Contract test an independent plugin package can run in its own CI."""

from lumis_fixture_plugin import MANIFEST, create_plugin

from lumis_sdk.testkit import assert_plugin_factory_contract


def test_plugin_factory_contract() -> None:
    instance = assert_plugin_factory_contract(create_plugin, MANIFEST)
    assert instance.name == "fixture-evidence"
