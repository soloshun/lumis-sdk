"""Minimal redaction for context sent to optional model gateways."""

import re

_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(?P<name>[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)"
    r"(?P<separator>\s*=\s*)(?P<value>[^\s]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)Bearer\s+[A-Za-z0-9._-]+")
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")


def redact_text(value: str) -> str:
    """Mask common secrets and email addresses before outbound model use.

    This is a defensive baseline, not a complete data-loss-prevention system.
    Integrations must still minimize input and apply organization-specific
    redaction before sending sensitive operational context to a provider.
    """
    redacted = _ASSIGNMENT_PATTERN.sub(r"\g<name>\g<separator>[REDACTED_SECRET]", value)
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED_TOKEN]", redacted)
    return _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)
