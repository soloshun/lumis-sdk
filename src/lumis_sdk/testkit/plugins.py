"""Reusable plugin SDK fixtures and contract assertions."""

from dataclasses import dataclass
from typing import Any

from lumis_sdk.domain import (
    PLUGIN_API_VERSION,
    PluginManifest,
)


@dataclass
class FakePluginFactory:
    """Deterministic callable plugin factory for package contract tests."""

    lumis_manifest: PluginManifest
    instance: object
    calls: int = 0

    def __call__(self) -> object:
        self.calls += 1
        return self.instance


def make_test_plugin_manifest(
    *,
    name: str = "fixture-plugin",
    version: str = "1.0.0",
    entry_point: str = "fixture",
) -> PluginManifest:
    """Create a compatible authority-free plugin manifest."""
    return PluginManifest.model_validate(
        {
            "apiVersion": PLUGIN_API_VERSION,
            "kind": "PluginManifest",
            "metadata": {"name": name, "version": version},
            "spec": {
                "entryPoint": entry_point,
                "capabilities": ["evidence_provider"],
                "supportStatus": "experimental",
                "sdk": {"minimum": "0.0.3", "maximumExclusive": "1.0.0"},
                "requiredAuthorities": [],
                "summary": "Deterministic plugin contract fixture.",
            },
        }
    )


def assert_plugin_factory_contract(
    factory: Any,
    expected_manifest: PluginManifest,
) -> object:
    """Validate the public factory shape and return its created implementation."""
    if not callable(factory):
        raise AssertionError("plugin entry point must be callable")
    manifest = PluginManifest.model_validate(getattr(factory, "lumis_manifest", None))
    if manifest != expected_manifest:
        raise AssertionError("plugin factory manifest differs from the static package manifest")
    instance = factory()
    if instance is None:
        raise AssertionError("plugin factory returned None")
    return instance
