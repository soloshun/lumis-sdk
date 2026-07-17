"""Strict vendor-neutral plugin manifest and compatibility contracts."""

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from .models import DomainModel

PLUGIN_API_VERSION: Literal["lumis.dev/v1"] = "lumis.dev/v1"
PLUGIN_KIND: Literal["PluginManifest"] = "PluginManifest"


class PluginCapability(StrEnum):
    """Public SDK extension surfaces a plugin may implement."""

    EVIDENCE_PROVIDER = "evidence_provider"
    INCIDENT_SOURCE = "incident_source"
    MEMORY_STORE = "memory_store"
    MODEL_GATEWAY = "model_gateway"
    REPORT_WRITER = "report_writer"


class PluginAuthority(StrEnum):
    """Sensitive runtime authorities that are never granted by discovery."""

    EXECUTION = "execution"
    FILESYSTEM = "filesystem"
    MODEL = "model"
    NETWORK = "network"
    SECRETS = "secrets"


class PluginSupportStatus(StrEnum):
    """Declared maintenance relationship for one plugin package."""

    OFFICIAL = "official"
    COMMUNITY = "community"
    EXPERIMENTAL = "experimental"
    ARCHIVED = "archived"


class PluginDiscoveryStatus(StrEnum):
    """Safe metadata-only discovery result."""

    COMPATIBLE = "compatible"
    DUPLICATE = "duplicate"
    INCOMPATIBLE = "incompatible"
    INVALID_MANIFEST = "invalid_manifest"
    MISSING_MANIFEST = "missing_manifest"


class PluginMetadata(DomainModel):
    """Stable plugin identity."""

    name: str = Field(pattern=r"^[a-z0-9]+(?:[-_.][a-z0-9]+)*$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")


class SdkCompatibility(DomainModel):
    """Supported Lumis SDK release interval."""

    minimum: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    maximum_exclusive: str = Field(
        alias="maximumExclusive",
        pattern=r"^\d+\.\d+\.\d+$",
    )

    @model_validator(mode="after")
    def require_non_empty_interval(self) -> "SdkCompatibility":
        if _version_tuple(self.minimum) >= _version_tuple(self.maximum_exclusive):
            raise ValueError("sdk minimum must be lower than maximumExclusive")
        return self


class PluginSpec(DomainModel):
    """Capabilities and authority requests declared before package import."""

    entry_point: str = Field(alias="entryPoint")
    capabilities: list[PluginCapability] = Field(min_length=1)
    support_status: PluginSupportStatus = Field(alias="supportStatus")
    sdk: SdkCompatibility
    required_authorities: list[PluginAuthority] = Field(
        default_factory=list,
        alias="requiredAuthorities",
    )
    summary: str

    @model_validator(mode="after")
    def require_unique_declarations(self) -> "PluginSpec":
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("plugin capabilities must be unique")
        if len(self.required_authorities) != len(set(self.required_authorities)):
            raise ValueError("plugin requiredAuthorities must be unique")
        return self


class PluginManifest(DomainModel):
    """Metadata shipped as ``lumis-plugin.json`` in a plugin distribution."""

    api_version: Literal["lumis.dev/v1", "lumis.dev/v1alpha1"] = Field(alias="apiVersion")
    kind: Literal["PluginManifest"] = PLUGIN_KIND
    metadata: PluginMetadata
    spec: PluginSpec


class PluginDescriptor(DomainModel):
    """One isolated plugin discovery result."""

    name: str
    distribution: str
    distribution_version: str
    entry_point: str
    status: PluginDiscoveryStatus
    message: str
    support_status: PluginSupportStatus | None = None
    capabilities: list[PluginCapability] = Field(default_factory=list)
    required_authorities: list[PluginAuthority] = Field(default_factory=list)


class PluginLoadPolicy(DomainModel):
    """Explicit capabilities and sensitive authorities allowed during loading."""

    allowed_capabilities: list[PluginCapability] = Field(
        default_factory=lambda: list(PluginCapability)
    )
    allowed_authorities: list[PluginAuthority] = Field(default_factory=list)


def plugin_manifest_json_schema() -> dict[str, object]:
    """Return the checked JSON Schema for independently packaged plugins."""
    return _manifest_schema(PLUGIN_API_VERSION)


def legacy_plugin_manifest_json_schema() -> dict[str, object]:
    """Return the frozen deprecated plugin manifest schema."""
    return _manifest_schema("lumis.dev/v1alpha1")


def _manifest_schema(version: str) -> dict[str, object]:
    schema = PluginManifest.model_json_schema(by_alias=True)
    marker = schema["properties"]["apiVersion"]
    assert isinstance(marker, dict)
    marker.pop("enum", None)
    marker["const"] = version
    return schema


def _version_tuple(value: str) -> tuple[int, int, int]:
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)
