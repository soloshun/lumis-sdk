"""Plugin package contracts."""

from typing import Protocol

from lumis_sdk.domain import PluginDescriptor, PluginManifest


class PluginFactory(Protocol):
    """Explicitly loaded factory exported by a plugin entry point."""

    lumis_manifest: PluginManifest

    def __call__(self) -> object:
        """Create the capability implementation without receiving implicit authority."""


class PluginCatalog(Protocol):
    """Discover plugin metadata without importing plugin modules."""

    def discover(self) -> list[PluginDescriptor]:
        """Return isolated metadata and compatibility results."""
