# Notebook playground

Start with [sdk-playground.ipynb](sdk-playground.ipynb). Select **Lumis SDK playground**, then
**Restart Kernel and Run All Cells**. It takes seconds once dependencies are installed.

The complete synthetic inputs are in [synthetic/](synthetic/):

- [lumis.yaml](synthetic/lumis.yaml): approved sources, graph, queries, signature and code scope.
- [incident.json](synthetic/incident.json): fictional incident identity and observation window.
- [telemetry.json](synthetic/telemetry.json): synthetic Prometheus/Loki/Tempo/Prefect responses.
- [features.py](synthetic/features.py): read-only inspection target; it is never executed.

The notebook displays SDK SVG graphs, tables of evidence/findings/receipts, an illustrative latency
chart, a scripted investigator, a Pydantic AI text stream, failure cases and SQLite audit records.
It makes no real HTTP/model calls and does not require Kubernetes, Docker or an API key.
Streaming prose is separate from the final validated SDK report; it never becomes evidence.

## Setup without disturbing your SDK environment

From the SDK checkout, create a separate notebook environment (do not overwrite an existing one):

```bash
uv venv ~/.local/share/lumis-sdk/notebook-env
uv pip install --python ~/.local/share/lumis-sdk/notebook-env/bin/python \
  -e '.[agent]' ipykernel nbclient nbformat nbconvert
~/.local/share/lumis-sdk/notebook-env/bin/python -m ipykernel install --user \
  --name lumis-sdk-playground --display-name 'Lumis SDK playground'
```

If the environment already exists, reuse it after checking its interpreter and SDK source path.
Select the named kernel in your notebook editor. The first cell prints the interpreter, package
version and actual SDK source location. This walkthrough expects an editable local checkout with
the current operational connectors, not an older package that has the same version string.
No Jupyter server is started automatically. Use your existing editor/Jupyter installation.

Each complete run copies the approved YAML/source into a fresh temporary directory and writes
its graphs, JSON report and SQLite audit there. The notebook prints that path. Re-run from the
top for a clean experiment; editing synthetic inputs changes expected assertions intentionally.
Outputs in the source notebook are cleared so repeated execution remains reproducible.

## Expected checkpoints

- Discovery completes and adds observed trace/service and workflow/run/task relationships.
- Full estate, incident neighborhood and proposed candidate path render as SVGs.
- The known signature takes the deterministic route with zero model requests.
- Missing logs escalate to the scripted investigator; its candidate is supported but unconfirmed.
- The separate scripted text stream produces multiple chunks without a remote model.
- Capped logs are degraded; unavailable traces leave the candidate unresolved.
- Audit roundtrips pass and the inspected source is unchanged.

All assertions pass with the original fixtures. These are contract demonstrations, not model
quality measurements or live incident qualification.

The older [graph notebook](operational-graph.ipynb) and [agent notebook](incident-agent.ipynb)
remain available as smaller focused examples; this playground does not replace your local edits.
