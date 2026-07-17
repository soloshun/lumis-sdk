# Plugin compatibility and support policy

The plugin manifest is a checked stable `lumis.dev/v1` public contract. Historical alpha
manifests remain readable during the documented compatibility window.

## Version intervals

- `sdk.minimum` is inclusive.
- `sdk.maximumExclusive` is exclusive.
- Both values use semantic `major.minor.patch` release numbers.
- Plugins should declare the narrowest interval they test in CI.
- A plugin release must update its manifest version to match its distribution version.

An incompatible plugin is visible to listing and doctor commands but cannot be loaded.

## Support status

| Status | Meaning |
| --- | --- |
| `official` | Maintained in the Lumis SDK governance boundary. |
| `community` | Maintained independently using public contracts. |
| `experimental` | Intended for evaluation; compatibility may change quickly. |
| `archived` | No longer loadable through the reference catalog. |

Support status is not a security endorsement. Users must review package ownership, provenance,
dependencies, permissions, release practices, and source code according to their own policy.

## Deprecation and migration

Breaking manifest or entry-point changes require an RFC and a new `apiVersion`. The SDK should
continue to diagnose old manifests with an actionable incompatibility message before removing
their parser. Plugin packages should publish overlapping releases during migration where
practical.

Core operation, local deterministic diagnosis, and all reference adapters remain functional when
no plugin is installed.
