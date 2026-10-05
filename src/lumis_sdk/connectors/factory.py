"""Compose HTTP evidence adapters only after the optional HTTP runtime is requested."""

import httpx

from lumis_sdk.runtime.investigation import EvidenceConnector
from lumis_sdk.runtime.project import Sources


def evidence_connectors(
    sources: Sources, client: httpx.AsyncClient
) -> dict[str, EvidenceConnector]:
    result: dict[str, EvidenceConnector] = {}
    if sources.prometheus.enabled:
        from lumis_sdk.connectors.prometheus import PrometheusConnector

        assert sources.prometheus.endpoint is not None
        result["prometheus"] = PrometheusConnector(sources.prometheus.endpoint, client)
    if sources.loki.enabled:
        from lumis_sdk.connectors.loki import LokiConnector

        result["loki"] = LokiConnector(sources.loki, client)
    if sources.tempo.enabled:
        from lumis_sdk.connectors.tempo import TempoConnector

        result["tempo"] = TempoConnector(sources.tempo, client)
    if sources.prefect.enabled:
        from lumis_sdk.connectors.prefect import PrefectConnector

        result["prefect"] = PrefectConnector(sources.prefect, client)
    return result
