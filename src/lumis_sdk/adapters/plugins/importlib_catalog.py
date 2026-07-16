"""Safe importlib.metadata plugin discovery."""

import json
import re
from dataclasses import dataclass
from importlib import metadata
from typing import Any

from pydantic import ValidationError

from lumis_sdk import __version__
from lumis_sdk.domain import (
    PLUGIN_API_VERSION,
    PluginDescriptor,
    PluginDiscoveryStatus,
    PluginLoadPolicy,
    PluginManifest,
    PluginSupportStatus,
)

PLUGIN_ENTRY_POINT_GROUP = "lumis_sdk.plugins"
PLUGIN_MANIFEST_FILENAME = "lumis-plugin.json"
MAX_PLUGIN_MANIFEST_BYTES = 65_536
_RELEASE_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


class PluginLoadError(RuntimeError):
    """A plugin failed closed during explicit loading."""


@dataclass(frozen=True)
class LoadedPlugin:
    """An explicitly loaded plugin implementation and its validated manifest."""

    manifest: PluginManifest
    instance: object


class ImportlibPluginCatalog:
    """Discover static manifests first and import only on an explicit load request."""

    def discover(self) -> list[PluginDescriptor]:
        """Read distribution metadata without importing plugin modules."""
        descriptors: list[PluginDescriptor] = []
        seen_names: set[str] = set()
        for entry_point in _plugin_entry_points():
            descriptor = _descriptor_from_entry_point(entry_point)
            if descriptor.name in seen_names:
                descriptor = descriptor.model_copy(
                    update={
                        "status": PluginDiscoveryStatus.DUPLICATE,
                        "message": "Another installed plugin declares the same manifest name.",
                    }
                )
            seen_names.add(descriptor.name)
            descriptors.append(descriptor)
        return sorted(descriptors, key=lambda item: (item.name, item.distribution))

    def load(
        self,
        name: str,
        *,
        policy: PluginLoadPolicy | None = None,
    ) -> LoadedPlugin:
        """Explicitly import and instantiate one compatible, authorized plugin."""
        load_policy = policy or PluginLoadPolicy()
        matches = [item for item in self.discover() if item.name == name]
        if len(matches) != 1:
            raise PluginLoadError(
                f"Expected one installed plugin named {name!r}; found {len(matches)}."
            )
        descriptor = matches[0]
        if descriptor.status is not PluginDiscoveryStatus.COMPATIBLE:
            raise PluginLoadError(f"Plugin {name!r} is not loadable: {descriptor.message}")
        denied_capabilities = set(descriptor.capabilities) - set(load_policy.allowed_capabilities)
        if denied_capabilities:
            denied = ", ".join(sorted(item.value for item in denied_capabilities))
            raise PluginLoadError(f"Plugin {name!r} requests disallowed capabilities: {denied}.")
        denied_authorities = set(descriptor.required_authorities) - set(
            load_policy.allowed_authorities
        )
        if denied_authorities:
            denied = ", ".join(sorted(item.value for item in denied_authorities))
            raise PluginLoadError(
                f"Plugin {name!r} requires authorities that were not explicitly granted: {denied}."
            )

        entry_point = next(
            (
                item
                for item in _plugin_entry_points()
                if item.name == descriptor.entry_point
                and _distribution_name(item) == descriptor.distribution
            ),
            None,
        )
        if entry_point is None:
            raise PluginLoadError(f"Plugin {name!r} disappeared after discovery.")
        try:
            factory = entry_point.load()
        except Exception as error:
            raise PluginLoadError(f"Plugin {name!r} could not be imported safely.") from error
        if not callable(factory):
            raise PluginLoadError(f"Plugin {name!r} entry point is not callable.")
        runtime_manifest_raw = getattr(factory, "lumis_manifest", None)
        try:
            runtime_manifest = PluginManifest.model_validate(runtime_manifest_raw)
        except ValidationError as error:
            raise PluginLoadError(
                f"Plugin {name!r} factory does not expose a valid lumis_manifest."
            ) from error
        static_manifest = _manifest_for_entry_point(entry_point)
        if runtime_manifest != static_manifest:
            raise PluginLoadError(
                f"Plugin {name!r} runtime manifest differs from its installed static manifest."
            )
        try:
            instance = factory()
        except Exception as error:
            raise PluginLoadError(f"Plugin {name!r} factory failed during creation.") from error
        return LoadedPlugin(manifest=runtime_manifest, instance=instance)


def _plugin_entry_points() -> list[Any]:
    return list(metadata.entry_points().select(group=PLUGIN_ENTRY_POINT_GROUP))


def _descriptor_from_entry_point(entry_point: Any) -> PluginDescriptor:
    distribution = _distribution_name(entry_point)
    distribution_version = str(getattr(entry_point.dist, "version", "unknown"))
    try:
        manifest = _manifest_for_entry_point(entry_point)
    except FileNotFoundError:
        return _failure_descriptor(
            entry_point,
            PluginDiscoveryStatus.MISSING_MANIFEST,
            f"Distribution must include {PLUGIN_MANIFEST_FILENAME}.",
        )
    except (OSError, json.JSONDecodeError, ValidationError, ValueError):
        return _failure_descriptor(
            entry_point,
            PluginDiscoveryStatus.INVALID_MANIFEST,
            "Static plugin manifest is invalid.",
        )

    status = PluginDiscoveryStatus.COMPATIBLE
    message = "Manifest is valid and compatible; plugin module has not been imported."
    if manifest.metadata.version != distribution_version:
        status = PluginDiscoveryStatus.INVALID_MANIFEST
        message = "Manifest version does not match the installed distribution version."
    elif manifest.spec.entry_point != entry_point.name:
        status = PluginDiscoveryStatus.INVALID_MANIFEST
        message = "Manifest entryPoint does not match the installed entry-point name."
    elif manifest.spec.support_status is PluginSupportStatus.ARCHIVED:
        status = PluginDiscoveryStatus.INCOMPATIBLE
        message = "Archived plugins fail closed and cannot be loaded."
    elif not _supports_sdk(manifest, __version__):
        status = PluginDiscoveryStatus.INCOMPATIBLE
        message = (
            f"Plugin supports SDK >= {manifest.spec.sdk.minimum} and "
            f"< {manifest.spec.sdk.maximum_exclusive}; installed SDK is {__version__}."
        )
    return PluginDescriptor(
        name=manifest.metadata.name,
        distribution=distribution,
        distribution_version=distribution_version,
        entry_point=entry_point.name,
        status=status,
        message=message,
        support_status=manifest.spec.support_status,
        capabilities=manifest.spec.capabilities,
        required_authorities=manifest.spec.required_authorities,
    )


def _failure_descriptor(
    entry_point: Any,
    status: PluginDiscoveryStatus,
    message: str,
) -> PluginDescriptor:
    distribution = _distribution_name(entry_point)
    return PluginDescriptor(
        name=entry_point.name,
        distribution=distribution,
        distribution_version=str(getattr(entry_point.dist, "version", "unknown")),
        entry_point=entry_point.name,
        status=status,
        message=message,
    )


def _manifest_for_entry_point(entry_point: Any) -> PluginManifest:
    raw = _read_static_manifest(entry_point.dist)
    if raw is None:
        raise FileNotFoundError(PLUGIN_MANIFEST_FILENAME)
    payload = json.loads(raw)
    manifest = PluginManifest.model_validate(payload)
    if manifest.api_version != PLUGIN_API_VERSION:
        raise ValueError("Unsupported plugin manifest version.")
    return manifest


def _read_static_manifest(distribution: Any) -> str | None:
    files = getattr(distribution, "files", None)
    if files is None:
        raw = distribution.read_text(PLUGIN_MANIFEST_FILENAME)
        if raw is None:
            return None
        if not isinstance(raw, str):
            raise ValueError("Plugin manifest must be UTF-8 text.")
        if len(raw.encode("utf-8")) > MAX_PLUGIN_MANIFEST_BYTES:
            raise ValueError("Plugin manifest exceeds the static metadata size limit.")
        return raw
    matches = [
        item
        for item in files
        if str(item).replace("\\", "/").split("/")[-1] == PLUGIN_MANIFEST_FILENAME
    ]
    if len(matches) != 1:
        return None
    path = distribution.locate_file(matches[0])
    if not path.is_file() or path.stat().st_size > MAX_PLUGIN_MANIFEST_BYTES:
        raise ValueError("Plugin manifest is missing or exceeds the static metadata size limit.")
    return str(path.read_text(encoding="utf-8"))


def _distribution_name(entry_point: Any) -> str:
    metadata_name = entry_point.dist.metadata.get("Name")
    return str(metadata_name or entry_point.name)


def _supports_sdk(manifest: PluginManifest, sdk_version: str) -> bool:
    current = _release_tuple(sdk_version)
    minimum = _release_tuple(manifest.spec.sdk.minimum)
    maximum = _release_tuple(manifest.spec.sdk.maximum_exclusive)
    return minimum <= current < maximum


def _release_tuple(value: str) -> tuple[int, int, int]:
    match = _RELEASE_PATTERN.match(value)
    if match is None:
        raise ValueError(f"Expected a semantic release version, received {value!r}.")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))
