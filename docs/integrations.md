# Application and cookbook boundaries

Lumis SDK is built, tested and released independently of applications.
GridCast is the first external testbed/cookbook, not a required Python dependency,
a required repository checkout, or a reason to pause framework development.

## Integration contract

1. Instrument the application using your chosen standard telemetry stack.
2. Configure Lumis externally with the explicitly scoped sources.
3. Declare external sources and optional identity aliases; enrich metadata without importing application code.
4. Register operator-owned observation queries and produce a bounded incident.
5. Supply normalized observations or register supported read-only observation queries in YAML.
6. Await `YamlProject.from_file("lumis.yaml").investigate(incident)`: discovery, binding,
   bounded context and testing are composed for you. Retain the uncertainty/audit record.

Kubernetes resource discovery, OTLP JSON topology, Prometheus instant queries and normalized
snapshots plus existing Prometheus service-graph metrics are the implemented boundaries.
Future vendor adapters must reuse the same contracts.
No workflow requires importing a consumer's simulation, hidden injected fault or ground-truth label.

## First read-only integration slice

An operator supplies one explicit Kubernetes context/namespace, an approved Prometheus endpoint,
existing service-graph metrics and scalar observation queries. For example, these source fields
can be used inside a complete project (query/candidate definitions remain operator-owned):

```yaml
project: {name: my-estate, environment: local}
sources:
  kubernetes: {enabled: true, context: my-approved-context, namespace: my-estate}
  prometheus:
    enabled: true
    endpoint: http://localhost:9090
    discover_service_graph: true
    service_namespace: my-estate
queries:
  - id: frontend-availability
    provider: prometheus
    entity_id: 'service:my-estate:frontend'
    key: up
    description: Frontend target availability at incident end
    parameters: {promql: 'min(up{job="frontend"})'}
initial_query_ids: [frontend-availability]
```

This intentionally omits business hypotheses; without rules or an explicitly invoked model it
collects the initial observation then normally abstains with no candidates. Add falsifiable
rules or approved model settings following the [YAML reference](configuration.md).
Sources must really expose the configured logical IDs; no placeholder node is fabricated.
For GridCast, choose its real namespace/context/service names and registered metrics, rather than
blindly copying this generic query. Do not use an injected fault manifest as an observation.

| Boundary | Shipped capability | Qualification still needed |
| --- | --- | --- |
| Kubernetes | Scoped read-only resources + app-label logical service links | Real RBAC, labels, context/namespace |
| Prometheus | Instant scalar evidence + service-graph vector discovery | Available metrics, correct estate scope/aggregation |
| OpenTelemetry | Bounded local OTLP JSON topology normalization | Approved export and service identities; not a live receiver |
| Dataset/job lineage | Declared or normalized external graph snapshots | Real external lineage export; no OpenLineage ingestion yet |
| Git / Prefect / Loki / Tempo queries | Not shipped | Future adapter milestones before dependent scenarios |
| Models | OpenRouter default; native OpenAI/Anthropic/Gemini | Live schema/quality/cost/privacy evaluation |

The cookbook's integration draft can describe future sources. A field in that draft is **not**
automatically supported SDK YAML: unknown fields fail validation. In particular Loki/Tempo/SQL/
Prefect providers, namespace arrays, arbitrary allowed actions and default-model shortcuts are not
accepted by the current schema. No cookbook code or deployment is changed by this SDK milestone.

### Acceptance checklist for each cookbook

- [ ] Install the intended SDK commit/version; do not confuse the old index release with dev.
- [ ] `lumis doctor` passes local validation; verify configured optional dependencies/tools.
- [ ] `lumis discover --report` completes against approved real sources.
- [ ] `lumis graph --entity CANONICAL_ID` includes expected dependency/resource identities.
- [ ] Register queries with correct aggregation and timezone-aware incident windows.
- [ ] Investigate without models first; retain queries, timestamps, provenance and abstention.
- [ ] Separately qualify optional live model candidates with withheld/conflicting evidence.
- [ ] Record versions, topology inputs, metrics, access limits and measured outcomes externally.

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
