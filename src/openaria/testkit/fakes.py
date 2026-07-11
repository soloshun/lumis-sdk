"""Deterministic test doubles for adapter contract and CI tests."""

from dataclasses import dataclass

from openaria.domain import DiagnosisResult, EvidenceItem, IncidentInput
from openaria.ports import ModelInvocation, ModelUsePolicy


@dataclass
class FakeModelGateway:
    """Return one predefined diagnosis without credentials or network access."""

    diagnosis: DiagnosisResult
    provider: str = "fake"
    model: str = "fake-model"
    calls: int = 0

    async def generate_diagnosis(
        self,
        *,
        incident: IncidentInput,
        evidence: list[EvidenceItem],
        policy: ModelUsePolicy,
    ) -> ModelInvocation:
        """Return a schema-valid invocation and record the call count."""
        self.calls += 1
        log_text = str(incident.raw_payload.get("log", ""))
        return ModelInvocation(
            diagnosis=self.diagnosis,
            provider=self.provider,
            model=self.model,
            prompt_version=policy.prompt_version,
            input_characters=len(log_text),
        )
