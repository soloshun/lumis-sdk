"""Execute trusted repository notebook cells offline; no Jupyter or remote kernel dependency."""

import ast
import asyncio
import inspect
import json
import sys
from pathlib import Path
from types import ModuleType
from xml.etree import ElementTree

import pytest


@pytest.mark.parametrize("name", ["operational-graph", "incident-agent", "sdk-playground"])
def test_operational_graph_notebook_runs_all_cells(tmp_path, monkeypatch, name):
    drawings = []
    if name == "sdk-playground":
        # Mock the notebook UI only; connectors, graph, agent and streaming protocol are real.
        # The actual Jupyter kernel/render is also checked separately during authoring.
        display_module = ModuleType("IPython.display")

        class Panel:
            def update(self, value):
                pass

        def drawing(value):
            ElementTree.fromstring(value)
            drawings.append(value)
            return value

        display_module.SVG = drawing
        display_module.HTML = lambda value: value
        display_module.display = lambda *args, **kwargs: Panel()
        ipython = ModuleType("IPython")
        ipython.get_ipython = lambda: None
        monkeypatch.setitem(sys.modules, "IPython", ipython)
        monkeypatch.setitem(sys.modules, "IPython.display", display_module)
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
        elif name == "incident-agent":
            assert namespace["report"].metrics.model_requests == 4
            assert namespace["triage_only"].route == "human"
        else:
            assert namespace["deterministic_report"].route == "deterministic"
            assert namespace["agent_report"].metrics.model_requests == 8
            assert namespace["failure_report"].assessments[0].state == "unresolved"
            assert len(namespace["stream_chunks"]) >= 2
            assert len(drawings) == 4  # Estate, neighborhood, candidate path and latency chart.
            assert len(namespace["estate"].entities) == 9
            assert {row["host"] for row in namespace["http_calls"]} == {
                "prometheus.synthetic.test",
                "loki.synthetic.test",
                "tempo.synthetic.test",
                "prefect.synthetic.test",
            }

    asyncio.run(execute())
