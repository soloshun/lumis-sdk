"""Tests for the optional, provider-neutral model boundary."""

from openaria.llm import ModelAssistanceConfig, ModelDiagnosisRequest, diagnose_with_optional_model
from openaria.llm.redaction import redact_text


class FakeGateway:
    """A fixture-only gateway that captures a request and returns JSON."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.request: ModelDiagnosisRequest | None = None

    def complete_diagnosis(self, request: ModelDiagnosisRequest) -> str:
        self.request = request
        return self.response


def test_disabled_model_assistance_uses_deterministic_diagnosis() -> None:
    """The default path does not call a model gateway."""
    result = diagnose_with_optional_model("ERROR KeyError: 'Close'")

    assert result.triage.classification == "schema_change"
    assert result.confidence == 0.65


def test_enabled_gateway_receives_only_redacted_log_context() -> None:
    """Secrets and email addresses are removed before a gateway receives context."""
    fixture_response = diagnose_with_optional_model("ERROR KeyError: 'Close'").model_dump_json()
    gateway = FakeGateway(fixture_response)
    log_text = (
        "OPENROUTER_API_KEY=super-secret\n"
        "Authorization: Bearer another-secret\n"
        "Owner: person@example.com\n"
        "ERROR KeyError: 'Close'"
    )

    result = diagnose_with_optional_model(
        log_text,
        config=ModelAssistanceConfig(enabled=True, provider="fixture", model="fixture-model"),
        gateway=gateway,
    )

    assert result.triage.classification == "schema_change"
    assert gateway.request is not None
    assert "super-secret" not in gateway.request.redacted_log
    assert "another-secret" not in gateway.request.redacted_log
    assert "person@example.com" not in gateway.request.redacted_log
    assert "[REDACTED_SECRET]" in gateway.request.redacted_log
    assert "[REDACTED_TOKEN]" in gateway.request.redacted_log
    assert "[REDACTED_EMAIL]" in gateway.request.redacted_log


def test_invalid_model_response_falls_back_to_deterministic_diagnosis() -> None:
    """Unvalidated model text never becomes an OpenARIA diagnosis."""
    result = diagnose_with_optional_model(
        "ERROR KeyError: 'Close'",
        config=ModelAssistanceConfig(enabled=True, provider="fixture", model="fixture-model"),
        gateway=FakeGateway('{"classification": "schema_change"}'),
    )

    assert result.triage.classification == "schema_change"
    assert result.confidence == 0.65


def test_redaction_masks_common_values() -> None:
    """The standalone redactor documents the baseline transformations."""
    redacted = redact_text("API_TOKEN=abc Bearer def person@example.com")

    assert redacted == "API_TOKEN=[REDACTED_SECRET] Bearer [REDACTED_TOKEN] [REDACTED_EMAIL]"
