"""Plugin SDK manifest, discovery, loading, and contract tests."""

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from lumis_sdk.adapters.plugins import ImportlibPluginCatalog, PluginLoadError
from lumis_sdk.cli.app import app
from lumis_sdk.domain import (
    PluginAuthority,
    PluginDiscoveryStatus,
    PluginLoadPolicy,
    PluginSupportStatus,
)
from lumis_sdk.testkit import (
    FakePluginFactory,
    assert_plugin_factory_contract,
    make_test_plugin_manifest,
)

runner = CliRunner()


class FakeDistribution:
    def __init__(self, name: str, version: str, manifest: str | None) -> None:
        self.metadata = {"Name": name}
        self.version = version
        self._manifest = manifest

    def read_text(self, filename: str) -> str | None:
        assert filename == "lumis-plugin.json"
        return self._manifest


class FakeEntryPoint:
    def __init__(
        self,
        name: str,
        distribution: FakeDistribution,
        loaded: object,
    ) -> None:
        self.name = name
        self.dist = distribution
        self._loaded = loaded
        self.load_calls = 0

    def load(self) -> object:
        self.load_calls += 1
        return self._loaded


class FakeEntryPoints(list[FakeEntryPoint]):
    def select(self, *, group: str) -> "FakeEntryPoints":
        assert group == "lumis_sdk.plugins"
        return self


def _entry_point(
    *,
    name: str = "fixture",
    plugin_name: str = "fixture-plugin",
    version: str = "1.0.0",
    minimum: str = "0.0.3",
    maximum: str = "1.0.0",
    authorities: list[str] | None = None,
) -> tuple[FakeEntryPoint, FakePluginFactory]:
    manifest = make_test_plugin_manifest(name=plugin_name, version=version, entry_point=name)
    manifest = manifest.model_copy(
        update={
            "spec": manifest.spec.model_copy(
                update={
                    "sdk": manifest.spec.sdk.model_copy(
                        update={"minimum": minimum, "maximum_exclusive": maximum}
                    ),
                    "required_authorities": [
                        PluginAuthority(authority) for authority in authorities or []
                    ],
                }
            )
        }
    )
    factory = FakePluginFactory(manifest, instance={"provider": plugin_name})
    distribution = FakeDistribution(
        f"{plugin_name}-package",
        version,
        manifest.model_dump_json(by_alias=True),
    )
    return FakeEntryPoint(name, distribution, factory), factory


def _install_entry_points(monkeypatch: pytest.MonkeyPatch, *items: FakeEntryPoint) -> None:
    monkeypatch.setattr(
        "lumis_sdk.adapters.plugins.importlib_catalog.metadata.entry_points",
        lambda: FakeEntryPoints(items),
    )


def test_discovery_is_metadata_only_and_loading_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry_point, factory = _entry_point()
    _install_entry_points(monkeypatch, entry_point)
    catalog = ImportlibPluginCatalog()

    descriptors = catalog.discover()

    assert descriptors[0].status is PluginDiscoveryStatus.COMPATIBLE
    assert entry_point.load_calls == 0
    loaded = catalog.load("fixture-plugin")
    assert loaded.instance == {"provider": "fixture-plugin"}
    assert entry_point.load_calls == 1
    assert factory.calls == 1


def test_discovery_isolates_invalid_and_incompatible_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid, _ = _entry_point()
    invalid = FakeEntryPoint(
        "invalid",
        FakeDistribution("invalid-package", "1.0.0", "{"),
        object(),
    )
    incompatible, _ = _entry_point(
        name="future",
        plugin_name="future-plugin",
        minimum="9.0.0",
        maximum="10.0.0",
    )
    _install_entry_points(monkeypatch, valid, invalid, incompatible)

    descriptors = ImportlibPluginCatalog().discover()
    statuses = {item.name: item.status for item in descriptors}

    assert statuses["fixture-plugin"] is PluginDiscoveryStatus.COMPATIBLE
    assert statuses["invalid"] is PluginDiscoveryStatus.INVALID_MANIFEST
    assert statuses["future-plugin"] is PluginDiscoveryStatus.INCOMPATIBLE
    assert invalid.load_calls == 0
    assert incompatible.load_calls == 0


def test_duplicate_manifest_names_and_archived_plugins_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, _ = _entry_point(name="first", plugin_name="duplicate-plugin")
    second, _ = _entry_point(name="second", plugin_name="duplicate-plugin")
    archived, _ = _entry_point(name="archived", plugin_name="archived-plugin")
    archived_manifest = make_test_plugin_manifest(
        name="archived-plugin",
        entry_point="archived",
    )
    archived_manifest = archived_manifest.model_copy(
        update={
            "spec": archived_manifest.spec.model_copy(
                update={"support_status": PluginSupportStatus.ARCHIVED}
            )
        }
    )
    archived.dist = FakeDistribution(
        "archived-plugin-package",
        "1.0.0",
        archived_manifest.model_dump_json(by_alias=True),
    )
    _install_entry_points(monkeypatch, first, second, archived)

    descriptors = ImportlibPluginCatalog().discover()

    assert [item.status for item in descriptors if item.name == "duplicate-plugin"] == [
        PluginDiscoveryStatus.COMPATIBLE,
        PluginDiscoveryStatus.DUPLICATE,
    ]
    archived_result = next(item for item in descriptors if item.name == "archived-plugin")
    assert archived_result.status is PluginDiscoveryStatus.INCOMPATIBLE


def test_sensitive_authorities_fail_closed_until_explicitly_granted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry_point, _ = _entry_point(authorities=["network"])
    _install_entry_points(monkeypatch, entry_point)
    catalog = ImportlibPluginCatalog()

    with pytest.raises(PluginLoadError, match="not explicitly granted"):
        catalog.load("fixture-plugin")

    loaded = catalog.load(
        "fixture-plugin",
        policy=PluginLoadPolicy(allowed_authorities=[PluginAuthority.NETWORK]),
    )
    assert loaded.instance == {"provider": "fixture-plugin"}


def test_factory_contract_is_reusable_by_independent_packages() -> None:
    manifest = make_test_plugin_manifest()
    factory = FakePluginFactory(manifest, instance=object())

    assert assert_plugin_factory_contract(factory, manifest) is factory.instance


def test_static_manifest_is_strict_json() -> None:
    manifest = make_test_plugin_manifest()
    payload: dict[str, Any] = json.loads(manifest.model_dump_json(by_alias=True))

    assert payload["kind"] == "PluginManifest"
    assert payload["spec"]["requiredAuthorities"] == []


def test_plugin_cli_is_safe_when_no_plugins_are_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_entry_points(monkeypatch)

    listed = runner.invoke(app, ["plugins", "list"])
    doctor = runner.invoke(app, ["plugins", "doctor", "--json"])

    assert listed.exit_code == 0
    assert "No Lumis SDK plugins installed." in listed.output
    assert doctor.exit_code == 0
    assert json.loads(doctor.output) == {"valid": True, "plugins": []}


def test_plugin_doctor_reports_invalid_metadata_without_importing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = FakeEntryPoint(
        "invalid",
        FakeDistribution("invalid-package", "1.0.0", "{"),
        object(),
    )
    _install_entry_points(monkeypatch, invalid)

    result = runner.invoke(app, ["plugins", "doctor", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["valid"] is False
    assert payload["plugins"][0]["status"] == "invalid_manifest"
    assert invalid.load_calls == 0
