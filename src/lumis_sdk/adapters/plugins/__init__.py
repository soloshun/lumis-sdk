"""Metadata-first plugin discovery and explicit loading."""

from .importlib_catalog import (
    MAX_PLUGIN_MANIFEST_BYTES,
    PLUGIN_ENTRY_POINT_GROUP,
    PLUGIN_MANIFEST_FILENAME,
    ImportlibPluginCatalog,
    LoadedPlugin,
    PluginLoadError,
)

__all__ = [
    "MAX_PLUGIN_MANIFEST_BYTES",
    "PLUGIN_ENTRY_POINT_GROUP",
    "PLUGIN_MANIFEST_FILENAME",
    "ImportlibPluginCatalog",
    "LoadedPlugin",
    "PluginLoadError",
]
