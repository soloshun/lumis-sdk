"""Synthetic independently packaged Lumis SDK plugin."""

from dataclasses import dataclass
from pathlib import Path

from lumis_sdk.domain import PluginManifest

MANIFEST = PluginManifest.model_validate_json(
    (Path(__file__).parents[1] / "lumis-plugin.json").read_text(encoding="utf-8")
)


@dataclass(frozen=True)
class FixtureEvidencePlugin:
    """An authority-free synthetic capability implementation."""

    name: str = "fixture-evidence"


class FixturePluginFactory:
    """Callable entry point carrying the validated runtime manifest."""

    lumis_manifest = MANIFEST

    def __call__(self) -> FixtureEvidencePlugin:
        return FixtureEvidencePlugin()


create_plugin = FixturePluginFactory()
