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
6. Await `YamlProject.from_file("lumis.yaml").handle_incident(incident)`: discovery, binding,
   triage, optional tool-agent investigation and mechanical reporting are composed for you.
   Retain the uncertainty/audit record. Enable paid agents explicitly with use_agent=True.

Kubernetes discovery, OTLP exports, Prometheus queries/service-graph metrics, normalized snapshots,
Loki logs, Tempo traces and Prefect run observations/topology are implemented boundaries.
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

This intentionally omits diagnostic signatures; without checks or an explicitly enabled agent
it collects the initial observation then reports requires_human_expert. Add falsifiable checks
or approved model settings following the [incident guide](incident-investigation.md).
Sources must really expose the configured logical IDs; no placeholder node is fabricated.
For GridCast, choose its real namespace/context/service names and registered metrics, rather than
blindly copying this generic query. Do not use an injected fault manifest as an observation.

| Boundary | Shipped capability | Qualification still needed |
| --- | --- | --- |
| Kubernetes | Scoped read-only resources + app-label logical service links | Real RBAC, labels, context/namespace |
| Prometheus | Instant scalar evidence + service-graph vector discovery | Available metrics, correct estate scope/aggregation |
| OpenTelemetry | Bounded local OTLP JSON topology normalization | Approved export and service identities; not a live receiver |
| Dataset/job lineage | Declared or normalized external graph snapshots | Real external lineage export; no OpenLineage ingestion yet |
| Git inspection | Approved local file snapshot and bounded log/full-SHA diff | Real repository/file/entity mapping; typed recent-change queries not implemented yet |
| Loki | Registered bounded incident-window log queries | Actual labels/coverage, read credentials and log privacy |
| Tempo | TraceQL search, explicit trace spans and bounded trace-to-graph discovery | Resource identity/namespace, actual trace encoding and available backend history |
| Prefect | Scoped flow/task state/runtime queries and workflow/task topology | API base, approved flow names, run/state timestamps and permissions |
| SQL evidence queries | Not shipped | Reviewed external normalized observations or future adapter work |
| Models | OpenRouter default; native OpenAI/Anthropic/Gemini | Live schema/quality/cost/privacy evaluation |

Use the [Loki/Tempo/Prefect setup guide](telemetry-connectors.md) and complete YAML example for
these endpoint-backed providers. A field in an older cookbook/design draft is not automatically
valid SDK YAML: unknown fields still fail validation. SQL providers, namespace arrays, arbitrary
allowed actions and default-model shortcuts are not accepted. An OTLP ingestion endpoint is not
a retrieval source; use Tempo's query endpoint or a local OTLP export. No cookbook code or
deployment is changed by this SDK milestone.

### Acceptance checklist for each cookbook

- [ ] Install the intended SDK commit/version; do not confuse the old index release with dev.
- [ ] `lumis doctor` passes local validation; verify configured optional dependencies/tools.
- [ ] `lumis discover --report` completes against approved real sources.
- [ ] `lumis graph --entity CANONICAL_ID` includes expected dependency/resource identities.
- [ ] Register queries with correct aggregation and timezone-aware incident windows.
- [ ] Run handle_incident without an agent first; retain findings, evidence and uncertainty.
- [ ] Separately qualify the optional live tool-agent with withheld/conflicting evidence.
- [ ] Approve repository file scope and a dedicated sandbox before testing generated probes.
- [ ] Record versions, topology inputs, metrics, access limits and measured outcomes externally.

## Separate cookbook project

Application scenarios, container estates, fault injection, deployment scripts, dashboards and
walkthrough videos belong to the separate Lumis cookbooks project.
In the maintainer workspace it is a sibling `lumis-cookbooks/` directory.
Its GridCast recipe is work in progress and is owned by that project.
SDK CI does not build or import it. This repository includes only synthetic contract fixtures and
the small offline CLI scaffold; there is no embedded cookbook directory.

## Two distinct kinds of readiness

The current GridCast integration draft describes the earlier candidate-only API and some
future source fields. It must be mapped to the incident API/current schema before execution.
Begin with one scenario whose discriminating evidence is available through supported
Prometheus observations, topology and approved code/Git inspection. Do not assume all nine
scenario families are covered. See the [review and first-test checklist](review-guide.md).

**SDK milestone readiness:** contracts, isolated/mock adapter checks, budgets, failure behavior,
CLI/YAML docs and clean-wheel independent smoke pass.

**Consumer qualification:** the consumer's real telemetry, identity mapping, access control,
provider model behavior, incident quality and representative workload are validated separately.

A consumer failure may reveal an SDK bug; investigate it with an independent reproduction.
Do not mark live integration as complete without evidence, but do not use it as a prerequisite
to continue SDK development. No live GridCast run or real model-quality measurement is claimed
by the standalone test suite.
