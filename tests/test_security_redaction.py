"""Tests for evidence redaction at optional external boundaries."""

from openaria.security import redact_text, redact_value


def test_redaction_masks_common_values() -> None:
    redacted = redact_text(
        "api_key=abc Bearer def person@example.com 415-555-2671 123-45-6789 "
        "4111 1111 1111 1111 ghp_abcdefghijklmnopqrstuvwxyz AKIA1234567890ABCDEF"
    )

    for secret in (
        "abc",
        "person@example.com",
        "415-555-2671",
        "123-45-6789",
        "4111 1111 1111 1111",
        "ghp_abcdefghijklmnopqrstuvwxyz",
        "AKIA1234567890ABCDEF",
    ):
        assert secret not in redacted
    for marker in (
        "[REDACTED_SECRET]",
        "[REDACTED_TOKEN]",
        "[REDACTED_EMAIL]",
        "[REDACTED_PHONE]",
        "[REDACTED_SSN]",
        "[REDACTED_CARD]",
    ):
        assert marker in redacted


def test_redaction_handles_nested_tool_results() -> None:
    value = redact_value(
        {
            "owner": "person@example.com",
            "api_key": 1234,
            "items": ["password=unsafe"],
        }
    )

    assert value == {
        "owner": "[REDACTED_EMAIL]",
        "api_key": "[REDACTED_SECRET]",
        "items": ["password=[REDACTED_SECRET]"],
    }
