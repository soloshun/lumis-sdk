"""Application service for deterministic-first, optionally model-assisted diagnosis."""

from dataclasses import dataclass, field

from lumis_sdk.adapters.deterministic import diagnose_text
from lumis_sdk.config import DeterministicRule
from lumis_sdk.domain import DiagnosisResult, IncidentInput
from lumis_sdk.ports import ModelGateway, ModelUsePolicy


@dataclass(frozen=True)
class DiagnosisService:
    """Coordinate diagnosis without depending on a provider or hosted product."""

    rules: list[DeterministicRule]
    model_gateway: ModelGateway | None = None
    model_policy: ModelUsePolicy = field(default_factory=ModelUsePolicy)

    async def diagnose(self, incident: IncidentInput) -> DiagnosisResult:
        """Run deterministic diagnosis, then bounded model reasoning only when allowed."""
        log_text = str(incident.raw_payload.get("log", ""))
        deterministic = diagnose_text(log_text, self.rules)
        if deterministic.triage.classification != "unknown":
            return deterministic
        if not self.model_policy.enabled or self.model_gateway is None:
            return deterministic
        invocation = await self.model_gateway.generate_diagnosis(
            incident=incident,
            evidence=deterministic.evidence,
            policy=self.model_policy,
        )
        return invocation.diagnosis
