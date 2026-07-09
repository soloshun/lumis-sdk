"""Safe routing between deterministic and optional model-assisted diagnosis."""

from pydantic import ValidationError

from openaria.llm.gateway import ModelAssistanceConfig, ModelGateway
from openaria.llm.prompts import build_diagnosis_request
from openaria.llm.redaction import redact_text
from openaria.schemas import DiagnosisResult
from openaria.triage import diagnose_log


def diagnose_with_optional_model(
    log_text: str,
    config: ModelAssistanceConfig | None = None,
    gateway: ModelGateway | None = None,
) -> DiagnosisResult:
    """Use a validated optional model result or the deterministic fallback.

    A model is never contacted unless both explicit configuration and a gateway
    implementation are supplied. Invalid structured output returns the same
    deterministic result rather than presenting unvalidated model text.
    """
    fallback = diagnose_log(log_text)
    model_config = config or ModelAssistanceConfig()
    if not model_config.enabled or gateway is None:
        return fallback

    request = build_diagnosis_request(redact_text(log_text))
    try:
        response = gateway.complete_diagnosis(request)
        return DiagnosisResult.model_validate_json(response)
    except (ValidationError, ValueError):
        return fallback
