"""Tests for evidence redaction at optional external boundaries."""

from lumis_sdk.security import redact_text, redact_value


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


def test_redaction_keeps_telemetry_numbers_dates_and_addresses() -> None:
    """Measurements must reach the investigator intact (found on a live GridCast estate)."""
    for text in (
        "rows_scanned 116245.83746",
        '"value": 1245.4931506849316',
        "ts 1791032878.856",
        "p95 0.09501834908088541",
        "date 2026-10-03",
        "at 2026-10-03T14:18:25Z",
        "client 172.20.0.3 port 5432",
        "count 1791032878",
    ):
        assert redact_text(text) == text


def test_redaction_still_masks_phone_shapes() -> None:
    for text in ("+44 20 7946 0958", "(415) 555-2671", "415.555.2671", "+14155552671"):
        assert "[REDACTED_PHONE]" in redact_text(f"call {text} now")
