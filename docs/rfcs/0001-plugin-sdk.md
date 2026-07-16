# RFC 0001: Lumis SDK plugin discovery and loading

**Status:** Accepted

**Target:** v0.3

**Decision date:** 2026-07-16

## Context

Lumis SDK needs independently packaged adapters without making observability, database, cloud,
model, or agent-framework packages mandatory core dependencies. Python entry points provide a
standard discovery mechanism, but importing every entry point during discovery would execute
third-party code before compatibility, support status, capability, or authority checks.

## Decision

Plugin distributions use the `lumis_sdk.plugins` entry-point group and include a strict static
`lumis-plugin.json` file at distribution root. Discovery locates that exact distribution-owned
file through `importlib.metadata`, applies a 64-KiB bound, and does not call `EntryPoint.load`.

The manifest declares:

- stable plugin name and installed distribution version;
- the matching entry-point name;
- one or more SDK capability surfaces;
- official, community, experimental, or archived support status;
- a minimum-inclusive and maximum-exclusive Lumis SDK version interval;
- sensitive runtime authorities requested by the plugin;
- a concise human-readable summary.

Discovery validates and reports each package independently. Missing, malformed, incompatible,
archived, duplicate, and version-mismatched plugins fail closed without preventing other plugins
from being inspected.

Loading is a separate explicit operation. The caller supplies a `PluginLoadPolicy`; network,
filesystem, secret, model, and execution authority default to denied. The loaded callable must
expose a runtime `lumis_manifest` equal to the installed static manifest before it creates an
implementation.

## Entry-point lifecycle

1. Install a plugin package through the user's normal package-management and review process.
2. `lumis plugins list` reads static metadata only.
3. `lumis plugins doctor` validates manifests and compatibility without importing modules.
4. Application code explicitly chooses a plugin and a load policy.
5. The catalog imports only that entry point, validates its runtime manifest, and invokes its
   zero-argument factory.
6. The consuming application composes the returned implementation with the relevant public port.

The SDK does not automatically activate, configure, call, retry, or grant credentials to a loaded
implementation.

## Capability negotiation

The v1alpha1 manifest supports `evidence_provider`, `incident_source`, `memory_store`,
`model_gateway`, and `report_writer`. A load policy may narrow this set. Declaring a capability
does not prove that an implementation satisfies its corresponding port; independent packages use
the reusable testkit contract assertion and capability-specific contract tests.

## Compatibility policy

Plugins declare `sdk.minimum` and `sdk.maximumExclusive` semantic release boundaries. The SDK
rejects packages outside that interval. Pre-1.0 plugin APIs may evolve between roadmap milestones;
plugins should use narrow tested intervals and publish a compatibility update before widening
them.

## Security consequences

- Static discovery does not import plugin code.
- A support label communicates maintenance relationship, not safety or trust.
- Installation itself remains a package supply-chain decision outside the SDK.
- Loading executes third-party Python and must remain explicit.
- Authority declarations are review metadata and policy inputs, not sandbox guarantees.
- No plugin can gain execution authority merely by being installed or discovered.

## Alternatives rejected

- Import every entry point to obtain its manifest: executes unreviewed code during inspection.
- Put manifests only in Python objects: prevents safe metadata-only tooling.
- Grant authority from declared capabilities: conflates interface shape with runtime permission.
- Add provider packages to core: violates vendor independence and enlarges every adopter's attack
  and dependency surface.
