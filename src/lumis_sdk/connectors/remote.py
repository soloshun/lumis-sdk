"""Shared read-only transport and normalization; credentials never become observations."""

import hashlib
import json
import math
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from lumis_sdk.connectors.http import read_payload, validate_endpoint
from lumis_sdk.connectors.settings import RemoteSource
from lumis_sdk.core import Evidence, EvidenceQuery, Incident


def nanoseconds(value: Any) -> datetime:
    return datetime.fromtimestamp(float(Decimal(str(value)) / Decimal(1_000_000_000)), UTC)


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return result


def numeric(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("expected numeric observation")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("invalid numeric observation")
    return result


class RemoteConnector:
    """Caller-owned client; fixed paths, no redirects, retries or executable payloads."""

    def __init__(self, source: RemoteSource, client: httpx.AsyncClient) -> None:
        if not source.enabled or source.endpoint is None:
            raise ValueError("enabled configured source required")
        self.source = source
        self.endpoint = validate_endpoint(source.endpoint)
        self.client = client
        self.requests = 0

    def headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        for header, variable in self.source.headers_env.items():
            value = os.environ.get(variable, "")
            if not value or "\n" in value or "\r" in value:
                raise ValueError("configured source credential unavailable or invalid")
            headers[header] = value
        return headers

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self.requests >= self.source.max_requests:
            raise ValueError("source request budget exhausted")
        self.requests += 1
        return await read_payload(
            self.client,
            method,
            self.endpoint + path,
            headers=self.headers(),
            max_bytes=self.source.max_response_bytes,
            **kwargs,
        )

    def text(self, value: dict[str, Any]) -> str:
        from lumis_sdk.security.redaction import redact_text

        result = json.dumps(value, ensure_ascii=False, allow_nan=False)
        for variable in self.source.headers_env.values():
            secret = os.environ.get(variable, "")
            if secret:
                result = result.replace(secret, "[REDACTED]")
                result = result.replace(json.dumps(secret)[1:-1], "[REDACTED]")
                # Authorization may include a scheme; also scrub the token itself.
                token = secret.split(" ", 1)[-1]
                if token:
                    result = result.replace(token, "[REDACTED]")
                    result = result.replace(json.dumps(token)[1:-1], "[REDACTED]")
        result = redact_text(result)
        if len(result) > 4000:
            raise ValueError("observation exceeds text bound")
        return result

    @staticmethod
    def fact(
        query: EvidenceQuery,
        incident: Incident,
        value: str | int | float,
        observed_at: datetime,
        index: int,
        path: str,
        *,
        degraded: bool = False,
    ) -> Evidence:
        if not incident.started_at <= observed_at <= incident.ended_at:
            raise ValueError("observation is outside incident window")
        return Evidence(
            id=f"{query.provider}:{hashlib.sha256(query.id.encode()).hexdigest()[:32]}:{index}",
            query_id=query.id,
            entity_id=query.entity_id,
            key=query.key,
            value=value,
            observed_at=observed_at,
            source=query.provider,
            retrieval_method=path,
            quality="degraded" if degraded else "observed",
        )
