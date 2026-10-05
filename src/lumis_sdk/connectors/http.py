"""Shared bounded HTTP reads; endpoints are operator configuration, not model input."""

import json
from typing import Any
from urllib.parse import urlsplit

import httpx


def validate_endpoint(endpoint: str) -> str:
    """Allow explicit HTTP(S) endpoints including local labs; reject embedded credentials."""
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("endpoint must be an HTTP(S) URL without credentials, query, or fragment")
    return endpoint.rstrip("/")


async def read_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_bytes: int = 1_000_000,
    **kwargs: Any,
) -> dict[str, Any]:
    result = await read_payload(client, method, url, max_bytes=max_bytes, **kwargs)
    if not isinstance(result, dict):
        raise ValueError("HTTP JSON response must be an object")
    return result


async def read_payload(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_bytes: int = 1_000_000,
    **kwargs: Any,
) -> Any:
    """Bound decoded response bytes, including chunked or compressed responses."""
    async with client.stream(method, url, follow_redirects=False, **kwargs) as response:
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError("redirects are not permitted")
        chunks = bytearray()
        async for chunk in response.aiter_bytes():
            if len(chunks) + len(chunk) > max_bytes:
                raise ValueError("HTTP response exceeds byte budget")
            chunks.extend(chunk)
    result = json.loads(chunks)
    return result
