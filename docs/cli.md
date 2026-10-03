# CLI walkthrough

Run these steps from the SDK repository, independently of any consuming application.
Use Python 3.11, 3.12 or 3.13. Install `uv` through your normal approved development setup.

## Incident workflow and interactive menu

The recommended new command is lumis incident, not the candidate-only investigate baseline:

    lumis incident --project lumis.yaml --incident incident.json \
      --observations observations.json --store audit/incidents.sqlite
    # Explicit paid-model permission, only if triage escalates:
    lumis incident --project lumis.yaml --incident incident.json --use-agent
    lumis console --project lumis.yaml
    lumis graph --project lumis.yaml --format terminal
    lumis graph --project lumis.yaml --format svg --output graph.svg
    lumis record-resolution --store audit/incidents.sqlite --resolution resolution.json --confirm

incident prints JSON; --store explicitly writes append-only SQLite. console provides a modest
ASCII menu for doctor, source inspection, graph and incident handling. Paid-agent permission
defaults to no. Machine-readable commands stay undecorated.
SVG writes a new file only and refuses overwrite; open it in a browser/image viewer.
The circular renderer needs no Graphviz/NumPy and caps images at 200 nodes/1000 edges;
terminal view caps 100/200. Use --entity ID --hops N for smaller neighborhoods.
Parallel edge labels may overlap; JSON/DOT retain the complete multigraph.
record-resolution requires an existing incident and explicit human attestation.
See [resolution fields](incident-investigation.md#reports-and-human-resolution).
No CLI command applies a fix or promotes a rule.

## 1. Install and inspect baseline commands

```bash
uv sync --all-groups
uv run lumis --version
uv run lumis --help
uv run lumis investigate --help
```

Expect the current checkout version and five commands: `init`, `doctor`,
`discover`, `graph`, `investigate`. Old diagnose/resolve/plugins/config-migrate commands are removed.
Do not assume the package currently on PyPI contains this unreleased reset.

## 2. Initialize a fresh workspace

```bash
uv run lumis init --directory /tmp/my-lumis-project
```

Expect `lumis.yaml`, `incident.json` and `observations.json`.
The YAML file uses JSON syntax (a valid YAML subset), for unambiguous typed values.
It describes one synthetic service, one registered health observation and one falsifiable
candidate. No network source or model is configured. Existing scaffold files are not overwritten.

## 3. Check configuration

```bash
uv run lumis doctor --project /tmp/my-lumis-project/lumis.yaml
```

Expect JSON with `valid: true`, `mode: "read_only"`, `network_checked: false` and
`warnings: []` for the default starter.
Doctor validates local configuration and reports missing optional tools/credentials/export files.
It does not connect to services, confirm RBAC, or spend model tokens.
Warnings do not invalidate an otherwise valid offline project. When discovery is configured,
doctor defers graph membership until preparation: `valid` is not proof that external IDs exist.
Invalid configuration exits nonzero with a sanitized error.

Read [YAML configuration](configuration.md) before enabling an external source.

## 4. Inspect declared or discovered topology

```bash
uv run lumis discover --project /tmp/my-lumis-project/lumis.yaml
```

Expect a graph JSON object with `entities` and `relationships`.
With the starter this is a local declared graph, with no external discovery.
If Kubernetes is enabled, this command reads only its configured context and namespace.
If OTLP export normalization is enabled, it reads that bounded local JSON file.
Enabled sources are reused automatically by investigation; there is no need to pass a saved
topology file just to run against the YAML sources. The incident context remains bounded separately.
Prometheus service-graph discovery and normalized topology files are also supported.

Inspect per-source status and the graph directly:

```bash
uv run lumis discover --project /tmp/my-lumis-project/lumis.yaml --report
uv run lumis graph --project /tmp/my-lumis-project/lumis.yaml --entity service:demo --hops 1
uv run lumis graph --project /tmp/my-lumis-project/lumis.yaml --format dot
```

Report output includes `complete`, `graph` and `sources` (`ok`, `disabled`, `error`, `not_checked`).
An enabled source failure exits nonzero; `--report` still emits sanitized diagnostics. Partial
discovery is never treated as ready. DOT export needs no Graphviz/Matplotlib installation;
rendering it is optional. See [graph API](graph.md).

To retain the output, redirect it to a new file:

```bash
uv run lumis discover --project /tmp/my-lumis-project/lumis.yaml > /tmp/my-lumis-project/topology.json
```

The shell redirect is your explicit file operation; the CLI does not rewrite your project YAML.

## 5. Run the offline investigation

```bash
uv run lumis investigate \
  --project /tmp/my-lumis-project/lumis.yaml \
  --incident /tmp/my-lumis-project/incident.json \
  --observations /tmp/my-lumis-project/observations.json \
  --topology /tmp/my-lumis-project/topology.json
```

Expect `outcome: "supported"`, `truth_state: "unconfirmed_hypothesis"`, one assessment
and an audited query. That result means the synthetic observation supports the candidate,
not that a real incident has been repaired or a root cause proven.

Run the same command without `--observations`: expect a valid `abstained` investigation.
Missing evidence is a normal result; the exit status remains zero.
Structural/input/provider setup errors exit nonzero.
`--topology` is optional additive enrichment, not a replacement for enabled YAML sources.
To make the two-input command shorter, set `observations_file: observations.json` in YAML, then
use only `--project` and `--incident`. That explicitly opts into file replay; the unchanged starter
still abstains when observations are omitted.

## 6. Persist a local audit record

Add `--store /tmp/my-lumis-project/investigations.sqlite` to step 5.
The store is local and append-only by incident ID: a duplicate incident ID fails rather than
silently overwriting history. Use a new incident ID for a distinct investigation.
The file's parent directory must exist. Protect audit files as potentially sensitive data.

## 7. Optional HTTP and model use

For a minimal source installation with HTTP dependencies:

```bash
uv sync --extra http
```

Enable/configure Prometheus and/or `models` in YAML (see [model providers](models.md)).
Provide the model key in the configured
environment variable using your approved secret-management method; never put it in YAML.
Use `--use-model` to opt in to a paid source call. OpenRouter is the default;
native OpenAI, Anthropic and Gemini are explicit alternatives. Merely configuring `models`
does not call it. Prometheus queries run when its registered queries are selected.
`--generation-only` returns candidates without the iterative evidence-testing loop; explicit
initial queries may still run and count toward the budget. It is not a no-network flag.

Provider availability and response quality require separate operator qualification.
Do not confuse mocked transport tests with a completed live-provider evaluation.

## Command reference

| Command / option | Effect |
| --- | --- |
| `init --directory PATH` | Create three offline starter files |
| `doctor --project FILE` | Local validation and readiness warnings only |
| `discover --project FILE` | Merge declared graph with explicitly enabled topology sources |
| `discover --project FILE --report` | Per-source acquisition status; nonzero for incomplete discovery |
| `graph --project FILE [--entity ID --hops N] [--format json or dot]` | Inspect discovered graph or bounded neighborhood |
| `investigate --project FILE --incident FILE` | Structured read-only investigation |
| `--observations FILE` | Replay normalized evidence JSON array |
| `--topology FILE` | Merge an external graph JSON snapshot |
| `--use-model` | Opt in to configured optional model source |
| `--generation-only` | Return candidates, not tested conclusions |
| `--store FILE` | Save immutable-ID investigation in SQLite |

Errors are deliberately sanitized to avoid exposing credentials, endpoint responses or private
payloads. Reproduce with synthetic files and use the Python API locally for detailed validation.
