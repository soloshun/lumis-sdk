"""Execute trusted repository notebook cells offline; no Jupyter or remote kernel dependency."""

import ast
import asyncio
import inspect
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("name", ["operational-graph", "incident-agent"])
def test_operational_graph_notebook_runs_all_cells(tmp_path, monkeypatch, name):
    monkeypatch.setattr("tempfile.mkdtemp", lambda **kwargs: str(tmp_path))
    path = Path(__file__).parents[1] / f"docs/notebooks/{name}.ipynb"
    document = json.loads(path.read_text())
    assert document["nbformat"] == 4
    assert document["nbformat_minor"] == 5
    assert len({cell["id"] for cell in document["cells"]}) == len(document["cells"])

    async def execute():
        namespace = {"__name__": "__notebook__"}
        for cell in document["cells"]:
            if cell["cell_type"] != "code":
                continue
            assert cell["outputs"] == [] and cell["execution_count"] is None
            compiled = compile(
                "".join(cell["source"]), str(path), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
            )
            # Only trusted, version-controlled example code; never a user-uploaded notebook.
            result = eval(compiled, namespace)  # noqa: S307
            if inspect.isawaitable(result):
                await result
        if name == "operational-graph":
            assert namespace["result"].outcome == "supported"
            assert namespace["missing"].outcome == "abstained"
            assert len(namespace["data_estate"].graph.snapshot().entities) == 3
        else:
            assert namespace["report"].metrics.model_requests == 4
            assert namespace["triage_only"].route == "human"

    asyncio.run(execute())
