# Application and cookbook boundaries

Lumis SDK is built, tested and released independently of applications.
GridCast is the first external testbed/cookbook, not a required Python dependency,
a required repository checkout, or a reason to pause framework development.

## Integration contract

1. Instrument the application using your chosen standard telemetry stack.
2. Configure Lumis externally with the explicitly scoped sources.
3. Normalize or discover topology; enrich declared metadata without importing application code.
4. Register operator-owned observation queries and produce a bounded incident.
5. Supply normalized observations or attach read-only evidence connectors.
6. Consume the structured investigation and retain its uncertainty/audit record.

Kubernetes resource discovery, OTLP JSON topology, Prometheus instant queries and normalized
snapshots are the implemented boundaries. Future vendor adapters must reuse the same contracts.
No workflow requires importing a consumer's simulation, hidden injected fault or ground-truth label.

## Separate cookbook project

Application scenarios, container estates, fault injection, deployment scripts, dashboards and
walkthrough videos belong to the separate Lumis cookbooks project.
In the maintainer workspace it is a sibling `lumis-cookbooks/` directory.
Its GridCast recipe is work in progress and is owned by that project.
SDK CI does not build or import it. This repository includes only synthetic contract fixtures and
the small offline CLI scaffold; there is no embedded cookbook directory.

## Two distinct kinds of readiness

**SDK milestone readiness:** contracts, isolated/mock adapter checks, budgets, failure behavior,
CLI/YAML docs and clean-wheel independent smoke pass.

**Consumer qualification:** the consumer's real telemetry, identity mapping, access control,
provider model behavior, incident quality and representative workload are validated separately.

A consumer failure may reveal an SDK bug; investigate it with an independent reproduction.
Do not mark live integration as complete without evidence, but do not use it as a prerequisite
to continue SDK development. No live GridCast run or real model-quality measurement is claimed
by the standalone test suite.
