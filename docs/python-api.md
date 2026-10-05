# Python API

Import the current operational contracts; there is no dependency on GridCast or its modules.

## Recommended incident API

Configured `loki`, `tempo` and `prefect` sources are composed automatically alongside
Prometheus and snapshot observations. Queries remain operator-registered; both deterministic
checks and agent `inspect(evidence)` use the same connectors. Optional Prefect/Tempo topology
is merged during `prepare()`. See the [endpoint/query guide](telemetry-connectors.md).

Use `YamlProject.handle_incident(...)` for evidence-backed triage, optional agent tools,
mechanical reports and human review. Read the [incident API/config/storage walkthrough](incident-investigation.md)
and executable [agent notebook](notebooks/incident-agent.ipynb).

The candidate-only investigate API below remains a comparison baseline; use_model is not a
tool-using agent loop.

## YAML-led candidate API

After `lumis init --directory /tmp/my-lumis-project`, optionally set
`observations_file: observations.json` in its YAML. The same project drives CLI and Python:

```python
from lumis_sdk.core import Incident
from lumis_sdk.runtime import YamlProject
from lumis_sdk.runtime.documents import read_document
from pathlib import Path

workspace = Path("/tmp/my-lumis-project")
incident = Incident.model_validate_json(read_document(workspace / "incident.json"))
project = YamlProject.from_file(workspace / "lumis.yaml")
result = await project.investigate(incident)
print(result.outcome, result.truth_state)
```

Use top-level `await` in Jupyter. In a regular Python script wrap the awaited code in `async def
main()` and call `asyncio.run(main())`; do not use `asyncio.run` inside an active notebook event loop.
The runnable [offline notebook](notebooks/operational-graph.ipynb) checks a service incident and
a separate data-lineage graph without any HTTP extra, cluster, credentials or consumer checkout.

`from_file` validates local configuration only. `investigate` discovers all enabled YAML sources
at the incident end time, strictly binds query/candidate entity IDs, then scopes the graph and
investigates. Sources/queries/hypotheses are declared once in YAML. No model call occurs unless
`use_model=True`; OpenRouter is the default configured provider, not a hidden default model.

For inspection or repeated incidents against an explicit shared snapshot:

```python
prepared = await project.prepare(at=incident.ended_at)
print(prepared.discovery.complete)
print([(source.name, source.status) for source in prepared.discovery.sources])
print(prepared.graph.upstream_of(incident.affected_entities[0]))
neighborhood = prepared.graph.dependencies_within(incident.affected_entities[0], hops=2)
networkx_graph = prepared.graph.to_networkx()  # independent deep copy
print(prepared.graph.to_dot())
result = await prepared.investigate(incident)
```

Reusing `PreparedProject` does not refresh topology; call `prepare` again for fresh discovery.
`client=` injects an `httpx.AsyncClient` for approved authenticated access or deterministic
transport tests; the caller retains ownership and must close it. Offline paths never import HTTP.
`topology=` adds a validated graph snapshot; `observations=` overrides configured replay facts.
`generation_only=True` returns candidates (initial observation queries may still run).

Preparation can raise `DiscoveryError`; inspect `error.report` (including incomplete source
statuses), not raw provider exception text. Missing discovered references raise `ValueError` before
investigation. Discovery and investigation have separate budgets; no automatic partial success,
global graph cache, live historical Kubernetes replay or automatic incident ingestion is implied.

## Lower-level extension API

Use this when adding custom source/connector implementations instead of the shipped YAML providers.

```python
import asyncio
from pathlib import Path
from pydantic import TypeAdapter

from lumis_sdk.core import Evidence, Incident
from lumis_sdk.connectors import SnapshotConnector
from lumis_sdk.graph import OperationalGraph
from lumis_sdk.reasoning import RuleSource
from lumis_sdk.runtime import InvestigationRuntime, InvestigationStore
from lumis_sdk.runtime.project import load_project, read_document

workspace = Path("/tmp/my-lumis-project")
project = load_project(workspace / "lumis.yaml")
incident = Incident.model_validate_json(read_document(workspace / "incident.json"))
facts = TypeAdapter(tuple[Evidence, ...]).validate_json(
    read_document(workspace / "observations.json")
)

runtime = InvestigationRuntime(
    graph=OperationalGraph(project.graph),
    queries=project.queries,
    sources=[RuleSource(project.rule_hypotheses)],
    connectors={"snapshot": SnapshotConnector(facts)},
    budget=project.budget,
)
result = asyncio.run(runtime.investigate(
    incident, initial_query_ids=project.initial_query_ids
))
print(result.model_dump_json(indent=2))
InvestigationStore(workspace / "investigations.sqlite").save(result)
```

Start by creating the workspace with `lumis init`. A duplicate stored incident ID fails.

## Extension ports

`HypothesisSource` exposes `name` and async `propose(context) -> tuple[Hypothesis, ...]`.
Use `RuleSource`, `MemoryHypothesisSource` for caller-retrieved candidates, or
`ModelHypothesisSource` with a model implementing async `generate(context)`.
Retrieval/rule-learning is not automatic; old candidates are revalidated and retested.

`EvidenceConnector` implements async `collect(query, incident) -> tuple[Evidence, ...]`.
Register the connector by provider name and its allowed catalog queries with the runtime.
The Python protocol supports additional caller-defined providers; the CLI configuration deliberately
accepts only the shipped snapshot and Prometheus providers.
Implement read-only, bounded, least-privilege access; never evaluate model-generated commands.

`OperationalGraph` exposes `upstream_of`, `downstream_of`, `dependencies_within`
and `scope`. Declare direction and provenance explicitly. Scope is bounded and cycle-safe.
Recent-change semantic queries and a persistent graph backend are not current APIs.

## Result contracts

`Investigation` contains version, context, assessments, trace, outcome, stop reason and
`truth_state="unconfirmed_hypothesis"`.
Assessment states: `supported`, `contradicted`, `unresolved`.
Outcomes: `supported`, `abstained`, `hypotheses_ready`.
See generated JSON schemas and [architecture](architecture.md) for invariants.

Optional HTTP adapters include `connectors.prometheus`, `connectors.loki`, `connectors.tempo`,
`connectors.prefect` and the four model wrappers documented in
[model providers](models.md). Core imports and local replay do not import HTTP dependencies.
There is intentionally no stable pre-reset API re-export or obsolete compatibility package.
