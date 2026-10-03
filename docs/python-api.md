# Python API

Import the current operational contracts; there is no dependency on GridCast or its modules.

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

Optional HTTP adapters include `connectors.prometheus` and the four model wrappers documented in
[model providers](models.md). Core imports and local replay do not import HTTP dependencies.
There is intentionally no stable pre-reset API re-export or obsolete compatibility package.
