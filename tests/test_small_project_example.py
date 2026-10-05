"""The documented small-project example (docs/small-project.md) behaves as the guide says."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from lumis_sdk.core import Incident
from lumis_sdk.runtime import YamlProject

EXAMPLE = Path(__file__).parents[1] / "docs/examples/small-project"


def _report(values: dict[str, str | None]):
    incident = Incident.model_validate(json.loads((EXAMPLE / "incident.json").read_text()))

    def handle(request: httpx.Request) -> httpx.Response:
        query = request.url.params["query"]
        value = next(v for metric, v in values.items() if metric in query)
        result = (
            []
            if value is None
            else [{"metric": {}, "value": [incident.ended_at.timestamp(), value]}]
        )
        return httpx.Response(
            200, json={"status": "success", "data": {"resultType": "vector", "result": result}}
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await YamlProject.from_file(EXAMPLE / "lumis.yaml").handle_incident(
                incident, client=client
            )

    return asyncio.run(run())


def test_both_signals_down_concludes_without_a_model() -> None:
    report = _report({"up{": "0", "probe_success": "0"})
    assert [f.status for f in report.findings] == ["match"]
    assert report.conclusion == "supported_diagnosis"


@pytest.mark.parametrize(
    ("values", "status"),
    [
        ({"up{": "1", "probe_success": "1"}, "no_match"),
        ({"up{": None, "probe_success": None}, "unknown"),
    ],
)
def test_healthy_or_missing_data_goes_to_a_person(
    values: dict[str, str | None], status: str
) -> None:
    report = _report(values)
    assert [f.status for f in report.findings] == [status]
    assert report.conclusion != "supported_diagnosis"
    assert report.route == "human"
