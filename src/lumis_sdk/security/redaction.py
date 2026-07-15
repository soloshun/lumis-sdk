"""Conservative redaction for evidence crossing an external model boundary."""

import re

_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?ix)\b(?P<name>[a-z0-9_-]*(?:api[_-]?key|access[_-]?token|"
    r"auth(?:entication)?[_-]?token|client[_-]?secret|password|passwd|secret|credential|"
    r"authorization|database[_-]?url)[a-z0-9_-]*)"
    r"(?P<separator>\s*[:=]\s*[\"']?)(?P<value>[^\s,\"']+)"
)
_BEARER_PATTERN = re.compile(r"(?i)Bearer\s+[A-Za-z0-9._-]+")
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d .()-]{7,}\d)(?!\w)")
_US_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_JWT_PATTERN = re.compile(r"\beyJ[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b")
_KNOWN_TOKEN_PATTERN = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{16,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b"
)
_CARD_CANDIDATE_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_SENSITIVE_FIELD_NAME_PATTERN = re.compile(
    r"(?ix)(?:api[_-]?key|access[_-]?token|auth(?:entication)?[_-]?token|"
    r"client[_-]?secret|password|passwd|secret|credential|authorization|database[_-]?url)"
)


def redact_text(value: str) -> str:
    """Mask common secrets and personal data before optional external use."""
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED_TOKEN]", value)
    redacted = _SENSITIVE_VALUE_PATTERN.sub(r"\g<name>\g<separator>[REDACTED_SECRET]", redacted)
    redacted = _KNOWN_TOKEN_PATTERN.sub("[REDACTED_TOKEN]", redacted)
    redacted = _JWT_PATTERN.sub("[REDACTED_TOKEN]", redacted)
    redacted = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)
    redacted = _US_SSN_PATTERN.sub("[REDACTED_SSN]", redacted)
    redacted = _CARD_CANDIDATE_PATTERN.sub(_redact_card_candidate, redacted)
    return _PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted)


def redact_value(value: object) -> object:
    """Recursively redact strings and sensitive keys in JSON-like values."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED_SECRET]"
                if _SENSITIVE_FIELD_NAME_PATTERN.search(str(key))
                else redact_value(item)
            )
            for key, item in value.items()
        }
    return value


def _redact_card_candidate(match: re.Match[str]) -> str:
    digits = re.sub(r"[ -]", "", match.group())
    return "[REDACTED_CARD]" if _passes_luhn(digits) else match.group()


def _passes_luhn(digits: str) -> bool:
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    for index, digit in enumerate(reversed(digits)):
        value = int(digit)
        if index % 2:
            value *= 2
            if value > 9:
                value -= 9
        checksum += value
    return checksum % 10 == 0
