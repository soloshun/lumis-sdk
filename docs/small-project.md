# Using Lumis on a small project

You do not need a large estate to try Lumis. This guide connects it to one service and a
Prometheus server, adds one deterministic check, and then (optionally) the investigator. The
complete, validated files are in [examples/small-project/](examples/small-project/).
For a large worked example, see the
[GridCast cookbook](https://github.com/soloshun/lumis-cookbooks/tree/main/gridcast). Smaller
cookbooks (a single web service, a single data pipeline) are planned.

## 1. Install

```bash
pip install "lumis-sdk[http]==0.1.0"          # add ,agent for the investigator, ,sql for SQL
```

## 2. Describe the service and what to read

[`examples/small-project/lumis.yaml`](examples/small-project/lumis.yaml) declares four things:

| Section | What it says |
|---|---|
| `sources.prometheus` | where to read metrics (read-only instant queries) |
| `graph.entities` | the one service, `service:api` |
| `queries` | two operator-owned PromQL queries, each producing one named fact (`up`, `probe_success`) |
| `checks` | one signature: "the API is down" predicts both facts are 0 and is falsified if either is 1 |

The model never writes PromQL. It may only ask for these queries by ID.

## 3. Check and run

```bash
lumis doctor --project lumis.yaml
lumis incident --project lumis.yaml --incident incident.json
```

`incident.json` names the affected entity and a time window. Queries are evaluated at the
window's end. Possible outcomes for the check:

| Finding | When | What happens next |
|---|---|---|
| `match` | both facts are 0 | the check is terminal, so triage concludes, with no model call |
| `no_match` | a falsifier holds (the API is up) | the incident goes to a person (or the investigator) |
| `unknown` | a query returned no data | the same: missing data is never treated as "down" |

## 4. Why the check looks like this

Lumis refuses to end triage on weak evidence, and the YAML enforces it:

- **A terminal check needs `explains_entities`** and **at least two distinct predicted facts**
  from independent queries. A single metric is a lead, not a conclusion. (Set `terminal: false`
  if you only have one signal.)
- **Both signals report a real 0 when the API is down.** Prometheus writes `up = 0` for a failed
  scrape, and a blackbox HTTP probe writes `probe_success = 0`. A request rate would not work
  here: when the process is down it stops producing samples, the query returns nothing, and Lumis
  records `unknown`. Avoid `or vector(0)` in queries; it turns "no data" into a false zero, which
  is the most common cause of wrong conclusions we have seen.

`--observations` replays facts only for `provider: snapshot` queries (see `lumis init`). It does
not override live Prometheus queries.

## 5. Add the investigator (optional)

When no check matches, an investigator can look further, still read-only and bounded:

```yaml
models:
  provider: openrouter            # or openai, anthropic, gemini
  model: deepseek/deepseek-v4-pro
  api_key_env: OPENROUTER_API_KEY
  reasoning: high
investigator:
  budget:
    request_limit: 12
```

```bash
pip install "lumis-sdk[http,agent]==0.1.0"
export OPENROUTER_API_KEY=...
lumis incident --project lumis.yaml --incident incident.json --use-agent
```

Configuration alone makes no paid call; only `--use-agent` does. The investigator can only use
your registered queries (plus code and Git you allowlist under `investigator.repositories`).
Each hypothesis it proposes is checked against facts Lumis collected itself, and it concludes
only when the supported hypotheses agree on one root cause.

## 6. Grow it

- More signals: Loki logs, Tempo traces, Prefect runs, read-only SQL, and typed change records
  from Git and Kubernetes rollouts. See [telemetry connectors](telemetry-connectors.md) and the
  [complete example](examples/telemetry-project.yaml).
- More services: add entities and `relationships`, or let Kubernetes and the Prometheus service
  graph discover them ([graph guide](graph.md)).
- Every field: the [YAML reference](configuration.md).
