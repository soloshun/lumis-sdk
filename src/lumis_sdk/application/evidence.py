"""Bounded evidence collection orchestration."""

import asyncio
from dataclasses import dataclass

from lumis_sdk.domain import (
    EvidenceCollection,
    EvidenceFailure,
    EvidenceItem,
    EvidenceRequest,
)
from lumis_sdk.ports import EvidenceProvider
from lumis_sdk.security import redact_text, redact_value


@dataclass(frozen=True)
class EvidenceService:
    """Apply timeout, filtering, redaction, deduplication, and size boundaries."""

    provider: EvidenceProvider
    timeout_seconds: float = 5.0

    async def collect(self, request: EvidenceRequest) -> EvidenceCollection:
        """Collect evidence while converting provider failures into safe results."""
        try:
            async with asyncio.timeout(self.timeout_seconds):
                collection = await self.provider.collect(request)
        except TimeoutError:
            return _failed_collection(
                self.provider.name,
                code="timeout",
                message="Evidence collection exceeded its configured time budget.",
                retryable=True,
            )
        except Exception:
            return _failed_collection(
                self.provider.name,
                code="provider_error",
                message="Evidence provider failed without returning a structured result.",
            )
        return _bound_collection(collection, request, provider_name=self.provider.name)


def _bound_collection(
    collection: EvidenceCollection,
    request: EvidenceRequest,
    *,
    provider_name: str,
) -> EvidenceCollection:
    items: list[EvidenceItem] = []
    seen_ids: set[str] = set()
    total_characters = 0
    truncated = collection.truncated
    requested_kinds = set(request.kinds)

    for item in collection.items:
        if requested_kinds and item.kind not in requested_kinds:
            continue
        if item.id in seen_ids:
            truncated = True
            continue
        detail = item.detail
        if request.redact:
            detail = redact_text(detail)
        if len(detail) > request.max_item_characters:
            detail = _truncate_detail(detail, request.max_item_characters)
            truncated = True
        if len(items) >= request.max_items:
            truncated = True
            break
        if total_characters + len(detail) > request.max_total_characters:
            truncated = True
            break
        seen_ids.add(item.id)
        total_characters += len(detail)
        items.append(_safe_item(item, detail, redact=request.redact))

    return EvidenceCollection(
        provider=provider_name,
        items=items,
        failures=collection.failures,
        truncated=truncated,
    )


def _safe_item(item: EvidenceItem, detail: str, *, redact: bool) -> EvidenceItem:
    if not redact:
        return item.model_copy(update={"detail": detail})
    reference = redact_text(item.reference) if item.reference is not None else None
    attributes = {key: str(redact_value(value)) for key, value in item.attributes.items()}
    return item.model_copy(
        update={
            "detail": detail,
            "reference": reference,
            "attributes": attributes,
        }
    )


def _truncate_detail(detail: str, limit: int) -> str:
    omitted = len(detail) - limit
    marker = f"... [{omitted} characters omitted]"
    if len(marker) >= limit:
        return marker[:limit]
    return f"{detail[: limit - len(marker)]}{marker}"


def _failed_collection(
    provider: str,
    *,
    code: str,
    message: str,
    retryable: bool = False,
) -> EvidenceCollection:
    return EvidenceCollection(
        provider=provider,
        failures=[
            EvidenceFailure(
                provider=provider,
                code=code,
                message=message,
                retryable=retryable,
            )
        ],
    )
