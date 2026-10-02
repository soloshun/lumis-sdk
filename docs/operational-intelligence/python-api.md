# Operational Python API (provisional)

All APIs here belong to the unreleased reset branch. Python 3.11–3.13. Install the reviewed
revision/wheel; `0.1.0rc1` on PyPI does not include this surface.

## Contracts

Import from `lumis_sdk.core`:

| Type | Required information/invariant |
| --- | --- |
| `Entity` | Unique ID, kind, name; normalized attributes/provenance |
| `Relationship` | Source, target, kind; both endpoints exist |
| `GraphSnapshot` | Unique entities/edges; serializable topology |
| `Incident` | ID, affected entities, symptoms, timezone-aware ordered window |
| `EvidenceQuery` | Registered ID, provider, entity, key, description; private parameters |
| `Evidence` | Unique ID, query, target/key, typed value, source, retrieval method, observed time |
| `Check` | Entity/key, eq/ne/gt/ge/lt/le comparison, typed scalar |
| `Hypothesis` | ID, statement, nonempty causal path/predictions/evidence requests/falsifiers |
| `IncidentContext` | Incident, scoped graph, catalog and observations; valid references/window |
| `InvestigationBudget` | Graph hops/entities, queries, hypotheses, context size and deadlines |
| `HypothesisAssessment` | Candidate, source labels, support/contradiction IDs, missing checks |
| `TraceStep` | Source/query/stop event, reference, reason, hypotheses, outcome status |
| `Investigation` | Versioned context, assessments, trace, terminal outcome, unconfirmed truth |

Unknown fields, non-finite scalars and invalid numeric comparisons are rejected. Attribute
assignment is frozen; callers must still treat nested metadata dictionaries as values, not
mutable shared state. Runtime/source boundaries copy or validate them. IDs must not encode secrets.

## Compose a replay

```python
import asyncio
from pathlib import Path
from pydantic import TypeAdapter
from lumis_sdk.connectors import SnapshotConnector
from lumis_sdk.core import Evidence, Incident
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.reasoning import RuleSource
from lumis_sdk.runtime import InvestigationRuntime, InvestigationStore
from lumis_sdk.runtime.project import load_project

root = Path("examples/gridcast-readonly")
project = load_project(root / "project.yaml")
incident = Incident.model_validate_json((root / "incident.json").read_text())
facts = TypeAdapter(tuple[Evidence, ...]).validate_json(
    (root / "observations.json").read_text()
)
runtime = InvestigationRuntime(
    graph=OperationalGraph(project.graph),
    sources=[RuleSource(project.rule_hypotheses)],
    queries=project.queries,
    connectors={"snapshot": SnapshotConnector(facts)},
    budget=project.budget,
)
result = asyncio.run(runtime.investigate(
    incident, initial_query_ids=project.initial_query_ids
))
print(result.model_dump_json(indent=2))
store = InvestigationStore(Path(".lumis/gridcast.sqlite"))
store.save(result)  # duplicate incident IDs reject instead of overwriting
assert store.get(incident.id) == result
```

`OperationalGraph.scope(seeds, hops=3, max_entities=100)` returns a snapshot.
`upstream_of`/`downstream_of` return sorted IDs excluding the seed. Unknown seeds or overflow
raise `ValueError`; cycles terminate. `snapshot()` returns a deep copy.

## Extension ports

`reasoning.HypothesisSource` has a read-only `name` property and
`async propose(context: IncidentContext) -> tuple[Hypothesis, ...]`.
`RuleSource`, `MemoryHypothesisSource` and `ModelHypothesisSource` all follow this port.
Memory retrieval is caller-owned: supply candidates from isolated episodes, not past evidence.
`reasoning.sources.HypothesisModel.generate(context)` is the replaceable model boundary.

`runtime.EvidenceConnector.collect(query: EvidenceQuery, incident: Incident)` returns a tuple
of observations. A tuple is intentionally bounded/non-streaming; the runtime rejects >100 items
per query and >50 candidates per source. Per-source/per-query/total deadlines apply. Cancellation
is propagated, not converted into a hidden model retry. Reuse a runtime across runs only with
connectors/sources whose own concurrency semantics you understand; per-run state is isolated.

`assess(hypothesis, context, sources)` provides mechanical check results. Register and validate
candidates through the runtime; standalone evaluation assumes valid context/candidate references.

## Optional providers

Install `lumis-sdk[http]` from the chosen Git revision or reviewed local wheel.

- `connectors.kubernetes.KubernetesDiscovery(namespace=..., context=...).discover()` returns
  a snapshot; relies on installed `kubectl`, kubeconfig and read-only RBAC.
- `connectors.kubernetes.topology_from_kubernetes(payload, namespace=...)` normalizes a Kubernetes
  List containing Services, Deployments, ReplicaSets and Pods. It strips env/secrets/annotations.
- `connectors.otel.topology_from_otlp(payload, max_spans=10000)` reads exported OTLP/JSON trace
  resource identity and parent-span links. It is not a receiver, trace backend or OTLP endpoint.
- `connectors.merge_topology(*snapshots)` merges provenance and compatible attributes; conflicts
  raise rather than override explicit declarations.
- `connectors.prometheus.PrometheusConnector(endpoint, client)` calls only `/api/v1/query` using
  operator-registered `parameters.promql` at incident end time. Exactly one scalar/vector sample
  is required; ambiguous multi-series responses fail. Operator chooses aggregation/units.
- `models.openrouter.OpenRouterHypothesisModel(model=..., api_key=SecretStr(...), client=...)`
  makes one bounded structured-output request. Explicit model and key are required. Output is
  3–5 candidates; registry revalidates graph/query references. It receives no tools.

Own/close injected `httpx.AsyncClient`, configure transport timeouts and credentials privately.
The CLI disables environment proxies. HTTP response bytes and redirects are bounded/rejected.
Configured local HTTP endpoints are allowed for the lab; operators must restrict network access
and credentials in their deployment. A model cannot change the registered endpoint/query.

## CLI and outcomes

`lumis discover --context kind-gridcast --namespace gridcast` prints resource topology JSON.
`lumis investigate --project project.yaml --incident incident.json --observations observations.json`
replays external normalized observations. Configure `prometheus_endpoint` and a query with provider
`prometheus` for live metrics. `--use-model` opts into OpenRouter using `openrouter_model` and
environment `OPENROUTER_API_KEY`. Never store a key in YAML. `--generation-only` stops after source
generation; `--store .lumis/investigations.sqlite` persists the result.

A schema/config/scope failure exits nonzero. A valid abstention exits zero with `outcome=abstained`;
automations must inspect outcome/stop reason rather than mistake command success for diagnosis.
Connector errors retain safe trace events, not raw error text. Stop reasons include
`supported_candidates`, `no_candidates`, `no_discriminating_query`, `budget_exhausted`,
`deadline_exceeded`, and `generation_only`.

## Wire schemas

Generated and checked by `scripts/generate_config_schema.py --check`:

- `schemas/lumis-operational-project-v1alpha1.schema.json`
- `schemas/lumis-investigation-v1alpha1.schema.json`

Both use `api_version: lumis.dev/operational-v1alpha1`. Legacy `apiVersion: lumis.dev/v1` is a
different envelope. Serialize via `model_dump_json`, validate via `model_validate_json`.
No stability promise is implied by the retained package version. See [migration](migration.md).
