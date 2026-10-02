# GridCast handoff: external read-only integration

GridCast is a separate synthetic testbed. Keep ingestion, feature, forecast and planning services
free of Lumis imports. Lumis runs beside them and reads standard telemetry/APIs or exported
snapshots. This contract is usable by other estates; no GridCast-specific domain code is in core.

## Inputs the GridCast runner should provide

1. **Topology:** services, database, forecast workflow and relevant deployment nodes. Declare
   workflow/business relationships; use namespace-scoped Kubernetes discovery and OTLP/JSON
   parent-span topology for discovered resources/calls. Bind logical service IDs to Kubernetes
   IDs explicitly. Merge compatible snapshots; don't silently equate same-looking names.
2. **Incident:** unique ID, affected logical entities, observed symptoms, UTC start/end window.
   Include a window sufficient for the desired observations. Detection remains GridCast/monitor
   owned; Lumis does not deploy an always-on anomaly detector in this slice.
3. **Observation catalog:** registered IDs, providers, target entity, normalized key, description,
   private provider parameters. Queries are bounded read-only observations, not actions.
4. **Facts:** unique ID, registered query ID, target/key, scalar, observation timestamp, source and
   retrieval method. Preserve degraded/unknown states rather than manufacturing normality.
5. **Candidate source:** rules/precedents for offline conformance; a chosen structured model for
   the actual 3–5 model-candidate milestone. Model output alone cannot confirm root cause.

For the query-amplification incident, useful observations are database read rate/baseline ratio,
feature deployment timing/diff, pipeline latency, database availability and service pressure.
The SDK ships only the read-only substrate: Git diff/deployment/Pipeline collectors should use
the observation port or be added when the real GridCast incident identifies the needed shape.

## Run the contract replay first

From the SDK checkout:

```bash
uv sync --all-groups
uv run lumis investigate \
  --project examples/gridcast-readonly/project.yaml \
  --incident examples/gridcast-readonly/incident.json \
  --observations examples/gridcast-readonly/observations.json
```

Expected: three candidates, one supported and two contradicted, four query events, unconfirmed
truth. To withhold all evidence, omit `--observations`; expect useful abstention with missing
checks. To examine just candidate generation add `--generation-only`.

## Connect a running lab

1. Start GridCast/telemetry using its own documented setup. Record revision, container images,
   Kubernetes version, namespace and telemetry endpoint. Do not configure production contexts.
2. Grant only `get/list` on Services, Deployments, Pods and ReplicaSets in the lab namespace.
   Use an explicit kubeconfig context. `lumis discover --context kind-gridcast --namespace gridcast`
   must produce resource topology JSON. Discovery requests no Secrets, ConfigMaps, shell or logs.
3. Normalize exported OTLP/JSON through `topology_from_otlp`; join declared workflow graph using
   `merge_topology`. Persist the input snapshots/revision beside evaluation results.
4. Set `prometheus_endpoint` in operational YAML. For each metric query choose provider
   `prometheus` and `parameters: {promql: <reviewed expression>}`. Use aggregation returning one
   value; define units/baseline explicitly. Keep deployment/health observations on independent
   registered connectors or snapshot imports. Do not mark fixture observations as live evidence.
5. Install the HTTP extra, choose `openrouter_model` supporting structured output, and supply
   `OPENROUTER_API_KEY` securely in the process environment. Invoke with `--use-model` only when
   paid generation is intended. The request carries no action tools and performs no retries.
6. Inject a fault from the **GridCast** runner. Do not put fault ID/root-cause manifest in the
   model context. Capture observations over an explicit incident window, then run investigation.
7. Inspect serialized graph, three-to-five model candidates, evidence provenance, every query
   and terminal reason. Retain output from both normal-evidence and withheld-evidence runs.
8. Score separately against the injector's ground truth. Record tokens/cost/provider/version.
   Declare live evidence complete only after this run; transport mocks are not sufficient.

## Artifact and cookbook boundary

Keep ground truth, injectors and baseline comparisons in the testbed/evaluation harness, separate
from the runtime observation bundle. A successful command is not recovery: there is no executor.
Do not add actuation to satisfy a demo without implementing the next roadmap's independent gates.

Small SDK conformance examples stay in `examples/`. A future `lumis-cookbooks` repository may
contain the full GridCast estate, setup/videos and larger scenarios once the maintainer creates
it. No new repository or copy of another agent's GridCast work is created by this refactor.
