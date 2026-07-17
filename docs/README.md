# Lumis SDK documentation

Lumis SDK is a vendor-agnostic Python framework for deterministic, evidence-grounded incident
diagnosis and carefully governed recovery workflows. Start with a core-only path; add models,
plugins, shared memory, or hosted systems only where the adopter explicitly needs them.

## Start here

| Goal | Guide |
| --- | --- |
| Understand the framework | [Core concepts](concepts/core-concepts.md) and [architecture overview](architecture/overview.md) |
| Install and run an example | [Cookbook guide](../cookbook/README.md) and [standalone adoption evidence](adoption/phase-1-standalone-paths.md) |
| Configure a project | [Configuration reference](configuration.md) |
| Migrate alpha documents | [v1 migration guide](migrations/config-v1.md) |
| Use the Python API | [Core API reference](LUMIS_SDK_REFERENCE.md) |
| Author a plugin | [Plugin API](python-api/plugins.md) and [compatibility policy](plugins/compatibility.md) |
| Review security boundaries | [Threat model](safety/threat-model.md) and [security review](safety/security-review.md) |
| Understand stability | [Public API inventory](stability/public-api.md) and [compatibility policy](stability/compatibility.md) |
| Reproduce performance checks | [Phase 1 bounded performance baseline](performance/phase-1-baseline.md) |
| Contribute or release | [Open-source project guide](architecture/open-source-project-guide.md) and [maintainer runbook](contributing/maintainer-runbook.md) |
| Review the 1.0 decision | [Release gate and evidence record](releases/1.0-release-gate.md) |
| See future direction | [Roadmap](../ROADMAP.md) and [candidate mapping](roadmap/candidate-capability-mapping.md) |

## Python API guides

- [Structured diagnosis rules](python-api/structured-rules.md)
- [Evidence and JSON reports](python-api/evidence-and-json-reports.md)
- [Memory stores](python-api/memory.md)
- [Connectors and webhooks](python-api/connectors.md)
- [Plugins](python-api/plugins.md)
- [Policy, verification, and learning](python-api/policy-verification-learning.md)

## Relatable walkthroughs

- [Prometheus/Alertmanager incident diagnosis](../cookbook/prometheus-alertmanager/README.md)
- [Custom PostgreSQL operational-memory schema](../cookbook/postgres-memory/README.md)
- [Data-pipeline investigation](../cookbook/data-pipeline-investigation/README.md)
- [ML regression monitoring](../cookbook/ml-regression-monitoring/README.md)
- [Software-delivery investigation](../cookbook/software-delivery-ci-investigation/README.md)
- [Phase 1 tutorial/video script](tutorials/phase-1-video-script.md)

Release-specific notes live under `docs/releases/`; accepted design decisions live under
`docs/rfcs/`. Product-specific Loomis platform behavior is intentionally outside this index.
