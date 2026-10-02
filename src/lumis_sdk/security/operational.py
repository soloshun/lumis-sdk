"""Redaction for model-facing operational contexts, without corrupting typed timestamps."""

from lumis_sdk.core import IncidentContext
from lumis_sdk.security.redaction import redact_text, redact_value


def redact_context(context: IncidentContext) -> IncidentContext:
    """Strip local query parameters and redact human/tool text and metadata.

    Identifiers are structural references: callers must never encode secrets in IDs. Times,
    scalar numbers, and check semantics remain untouched.
    """
    payload = context.model_dump(mode="json")
    payload["incident"]["symptoms"] = [redact_text(text) for text in context.incident.symptoms]
    for entity in payload["graph"]["entities"]:
        entity["name"] = redact_text(entity["name"])
        entity["attributes"] = redact_value(entity["attributes"])
    for query in payload["queries"]:
        query["description"] = redact_text(query["description"])
        query["parameters"] = {}
    for item in payload["evidence"]:
        if isinstance(item["value"], str):
            item["value"] = redact_text(item["value"])
    return IncidentContext.model_validate(payload)
