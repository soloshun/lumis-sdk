# Compatibility and deprecation policy

Lumis SDK uses semantic versioning for the stable `1.x` line. Before `1.0`, release numbers remain
development releases, but the project applies this policy to the surfaces explicitly marked
stable so adopters can rehearse upgrades.

## Compatibility matrix

| Area | 1.x guarantee | Not guaranteed |
| --- | --- | --- |
| Python | Python 3.11–3.13; documented stable imports keep source-compatible signatures or receive a deprecation path. | Private modules, undocumented keyword arguments, object identity, exception wording. |
| Configuration | `lumis.dev/v1` fields and meaning remain compatible; additive optional fields are allowed. | Unknown fields becoming accepted, implicit provider loading, plaintext secret values. |
| Serialized documents | Stable v1 envelopes remain parseable and preserve truth/evidence semantics. | Byte-for-byte JSON formatting or dictionary key order outside canonical-digest APIs. |
| Plugins | Static v1 manifests, capability names, authority checks, and SDK version intervals remain supported. | Loading a plugin whose declared interval excludes the installed SDK. |
| Persistence | `MemoryStore` contract behavior and truth transitions remain compatible. | SQLite/PostgreSQL physical schema, indexes, SQL, or direct database access. |
| CLI | Documented commands, option meaning, exit-code classes, and JSON keys remain compatible. | Human-readable spacing, ordering, and explanatory prose. |
| Schemas | Stable v1 schema constraints do not become incompatibly stricter in a minor release. | Provisional `v1alpha1` wire formats. |

Supported Python minors are tested in CI. Dropping a Python minor requires a major release unless
that Python version has reached end of life and continued support would prevent a security fix;
such an exception must be announced and documented.

## Deprecation lifecycle

1. A replacement and migration instructions are published.
2. A typed warning identifies the deprecated surface and planned removal release.
3. The old surface remains functional for the documented window.
4. Removal occurs only in the announced major release.

`lumis.dev/v1alpha1` project and rule documents are readable throughout `1.x` and are planned for
removal in `2.0`. Loaders emit `LumisV1Alpha1DeprecationWarning`, a `DeprecationWarning` subtype,
with the replacement, removal version, and migration guide. Stable projects must not mix v1 and
v1alpha1 files in one collection.

The other released alpha envelopes—diagnosis report, plugin manifest, playbook, and recovery
policy—also have validated v1 migrations. New SDK output and repository examples use v1. Alpha
schema files remain checked in so downstream validators can support historical artifacts.

## Reporting compatibility defects

Open a GitHub issue with the installed SDK version, Python version, smallest reproducer, expected
contract, and observed result. Security-sensitive incompatibilities should follow `SECURITY.md`
instead of a public issue.
