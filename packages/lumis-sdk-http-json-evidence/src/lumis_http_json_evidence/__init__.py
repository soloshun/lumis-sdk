"""Optional generic HTTP JSON EvidenceProvider plugin for Lumis SDK."""

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from lumis_sdk.config import HttpJsonEvidenceProviderConfig
from lumis_sdk.domain import (
    EvidenceCollection,
    EvidenceFailure,
    EvidenceItem,
    EvidenceRequest,
    PluginManifest,
)

_HEADER_NAME = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_MANIFEST_PATHS = (
    Path(__file__).with_name("lumis-plugin.json"),
    Path(__file__).parents[1] / "lumis-plugin.json",
    Path(__file__).parents[2] / "lumis-plugin.json",
)
MANIFEST = PluginManifest.model_validate_json(
    next(path for path in _MANIFEST_PATHS if path.is_file()).read_text(encoding="utf-8")
)


class HttpJsonEvidenceProvider:
    """Collect evidence from one strict allowlisted HTTPS JSON endpoint."""

    name = "http-json"

    def __init__(
        self,
        config: HttpJsonEvidenceProviderConfig,
        *,
        token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not _HEADER_NAME.fullmatch(config.auth_header):
            raise ValueError("authHeader must be a valid HTTP header name")
        if "\r" in config.auth_scheme or "\n" in config.auth_scheme:
            raise ValueError("authScheme must not contain newlines")
        if token is not None and ("\r" in token or "\n" in token):
            raise ValueError("HTTP evidence token must not contain newlines")
        self.config = config
        self._token = token
        self._transport = transport

    @classmethod
    def from_environment(
        cls,
        config: HttpJsonEvidenceProviderConfig,
        *,
        environ: Mapping[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> "HttpJsonEvidenceProvider":
        """Resolve only the configured token reference and retain no environment mapping."""
        token: str | None = None
        if config.token_env is not None:
            values = os.environ if environ is None else environ
            token = values.get(config.token_env)
            if not token:
                raise ValueError(
                    f"Required HTTP evidence environment variable {config.token_env!r} is not set"
                )
        return cls(config, token=token, transport=transport)

    async def collect(self, request: EvidenceRequest) -> EvidenceCollection:
        """Return normalized evidence or explicit bounded transport/response failures."""
        last = _failure("network_error", "HTTP evidence request did not run.", retryable=True)
        for _attempt in range(self.config.retries + 1):
            last = await self._collect_once(request)
            if not last.failures or not last.failures[0].retryable:
                return last
        return last

    async def _collect_once(self, request: EvidenceRequest) -> EvidenceCollection:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._token is not None:
            value = f"{self.config.auth_scheme} {self._token}".strip()
            headers[self.config.auth_header] = value
        payload = {
            "incident": {
                "sourceTool": request.incident.source_tool,
                "pipelineName": request.incident.pipeline_name,
                "environment": request.incident.environment,
            },
            "kinds": request.kinds,
            "limits": {
                "maxItems": request.max_items,
                "maxTotalCharacters": request.max_total_characters,
                "maxItemCharacters": request.max_item_characters,
            },
        }
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=self.config.timeout_seconds,
                follow_redirects=False,
            ) as client:
                async with client.stream(
                    "POST",
                    self.config.url,
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.is_redirect:
                        return _failure(
                            "redirect_not_allowed",
                            "HTTP evidence endpoint returned a redirect.",
                        )
                    if response.status_code >= 400:
                        return _failure(
                            "http_error",
                            f"HTTP evidence endpoint returned status {response.status_code}.",
                            retryable=response.status_code == 429 or response.status_code >= 500,
                        )
                    raw = await _read_bounded_response(
                        response,
                        max_bytes=self.config.max_response_bytes,
                    )
        except httpx.TimeoutException:
            return _failure(
                "timeout",
                "HTTP evidence request exceeded its configured timeout.",
                retryable=True,
            )
        except httpx.RequestError:
            return _failure(
                "network_error",
                "HTTP evidence request failed before a valid response.",
                retryable=True,
            )
        except ResponseTooLargeError:
            return _failure(
                "response_too_large",
                f"HTTP evidence response exceeds {self.config.max_response_bytes} bytes.",
            )
        return _parse_collection(raw)


class ResponseTooLargeError(ValueError):
    """Raised internally when streamed response bytes exceed the configured cap."""


async def _read_bounded_response(response: httpx.Response, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > max_bytes:
            raise ResponseTooLargeError
        chunks.append(chunk)
    return b"".join(chunks)


def _parse_collection(raw: bytes) -> EvidenceCollection:
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        DuplicateKeyError,
        NonFiniteJsonError,
        RecursionError,
    ):
        return _failure("invalid_response", "HTTP evidence response is not valid unique-key JSON.")
    items_raw = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items_raw, list):
        return _failure(
            "invalid_response",
            "HTTP evidence response must be an object containing an items array.",
        )
    try:
        items = [EvidenceItem.model_validate(item) for item in items_raw]
    except ValidationError:
        return _failure(
            "invalid_response",
            "HTTP evidence response contains an invalid evidence item.",
        )
    return EvidenceCollection(provider="http-json", items=items)


class DuplicateKeyError(ValueError):
    """Raised internally for ambiguous response objects."""


class NonFiniteJsonError(ValueError):
    """Raised internally for NaN and infinity JSON extensions."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKeyError
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise NonFiniteJsonError(value)


def _failure(
    code: str,
    message: str,
    *,
    retryable: bool = False,
) -> EvidenceCollection:
    return EvidenceCollection(
        provider="http-json",
        failures=[
            EvidenceFailure(
                provider="http-json",
                code=code,
                message=message,
                retryable=retryable,
            )
        ],
    )


@dataclass(frozen=True)
class HttpJsonEvidencePlugin:
    """Explicit composition surface returned by the plugin entry point."""

    name: str = "http-json-evidence"

    def create(
        self,
        config: HttpJsonEvidenceProviderConfig,
        *,
        environ: Mapping[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> HttpJsonEvidenceProvider:
        return HttpJsonEvidenceProvider.from_environment(
            config,
            environ=environ,
            transport=transport,
        )


class HttpJsonEvidencePluginFactory:
    """Callable plugin entry point carrying the validated runtime manifest."""

    lumis_manifest = MANIFEST

    def __call__(self) -> HttpJsonEvidencePlugin:
        return HttpJsonEvidencePlugin()


create_plugin = HttpJsonEvidencePluginFactory()

__all__ = [
    "HttpJsonEvidencePlugin",
    "HttpJsonEvidenceProvider",
    "MANIFEST",
    "create_plugin",
]
