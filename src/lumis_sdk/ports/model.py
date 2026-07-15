"""Provider-neutral model gateway port."""

from datetime import timedelta
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from lumis_sdk.domain import DiagnosisResult, EvidenceItem, IncidentInput


class ModelPortModel(BaseModel):
    """Strict base for model-boundary contracts."""

    model_config = ConfigDict(extra="forbid")


class ModelUsePolicy(ModelPortModel):
    """Explicit limits for one optional model-assisted diagnosis."""

    enabled: bool = False
    max_input_characters: int = Field(default=20_000, ge=1)
    max_output_tokens: int = Field(default=2_000, ge=1)
    max_tool_calls: int = Field(default=8, ge=0)
    timeout: timedelta = timedelta(seconds=30)
    prompt_version: str = "diagnosis-v1"


class ModelInvocation(ModelPortModel):
    """Auditable metadata returned with a model-assisted diagnosis."""

    diagnosis: DiagnosisResult
    provider: str
    model: str
    prompt_version: str
    input_characters: int
    output_tokens: int | None = None


class ModelGateway(Protocol):
    """Generate a structured diagnosis without exposing provider types to the domain."""

    async def generate_diagnosis(
        self,
        *,
        incident: IncidentInput,
        evidence: list[EvidenceItem],
        policy: ModelUsePolicy,
    ) -> ModelInvocation:
        """Return schema-validated diagnosis and invocation metadata."""
        ...
