# Plugin SDK

Lumis SDK plugins are independently packaged Python distributions discovered through static
metadata before any plugin module is imported.

## Package layout

Register one factory:

```toml
[project.entry-points."lumis_sdk.plugins"]
acme-evidence = "acme_lumis_plugin:create_plugin"

[tool.hatch.build.targets.wheel.force-include]
"lumis-plugin.json" = "lumis-plugin.json"
```

Ship `lumis-plugin.json` at distribution root:

```json
{
  "apiVersion": "lumis.dev/v1",
  "kind": "PluginManifest",
  "metadata": {
    "name": "acme-evidence",
    "version": "1.2.0"
  },
  "spec": {
    "entryPoint": "acme-evidence",
    "capabilities": ["evidence_provider"],
    "supportStatus": "community",
    "sdk": {
      "minimum": "0.0.4",
      "maximumExclusive": "0.1.0"
    },
    "requiredAuthorities": ["network", "secrets"],
    "summary": "Collect bounded evidence from the Acme service."
  }
}
```

The manifest version must equal the installed distribution version, and `entryPoint` must equal
the registered entry-point name. The static file is limited to 64 KiB.

## Factory contract

The entry point resolves to a zero-argument callable with a `lumis_manifest` attribute:

```python
from lumis_sdk.domain import PluginManifest

MANIFEST = PluginManifest.model_validate_json(...)


def create_plugin() -> object:
    return AcmeEvidenceProvider(...)


create_plugin.lumis_manifest = MANIFEST
```

Applications should normally wrap this shape in a typed callable class, as demonstrated by
`lumis_sdk.testkit.FakePluginFactory`.

## Discovery and loading

```python
from lumis_sdk.adapters.plugins import ImportlibPluginCatalog
from lumis_sdk.domain import PluginAuthority, PluginLoadPolicy

catalog = ImportlibPluginCatalog()
descriptors = catalog.discover()  # does not import plugin modules

loaded = catalog.load(
    "acme-evidence",
    policy=PluginLoadPolicy(
        allowed_authorities=[PluginAuthority.NETWORK, PluginAuthority.SECRETS]
    ),
)
provider = loaded.instance
```

The default load policy allows declared capability surfaces but denies every sensitive authority.
Loading also fails for missing/invalid manifests, incompatible SDK versions, archived plugins,
duplicates, entry-point mismatches, runtime/static manifest mismatches, import failures, and
factory failures.

## CLI

```bash
lumis plugins list
lumis plugins list --json
lumis plugins doctor
lumis plugins doctor --json
```

Both commands inspect static metadata only. They do not load or activate plugins.

## Contract testing

Independent packages can use:

```python
from lumis_sdk.testkit import assert_plugin_factory_contract

instance = assert_plugin_factory_contract(create_plugin, MANIFEST)
```

Capability-specific packages should additionally run the contract tests for the public port they
implement. The plugin factory check does not prove network safety, credential handling, semantic
correctness, or provider quality.

See [RFC 0001](../rfcs/0001-plugin-sdk.md) and the
[plugin compatibility policy](../plugins/compatibility.md).
