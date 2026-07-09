"""Interfaces for optional structured model assistance."""

from typing import Protocol

from pydantic import BaseModel


class ModelAssistanceConfig(BaseModel):
    """Configuration for an optional provider integration.

    Model assistance is off by default so the core diagnosis loop remains fully
    usable without credentials, a network connection, or a chosen provider.
    """

    enabled: bool = False
    provider: str | None = None
    model: str | None = None


class ModelDiagnosisRequest(BaseModel):
    """The minimized and redacted context permitted to leave the core."""

    prompt: str
    redacted_log: str


class ModelGateway(Protocol):
    """A provider adapter that returns a JSON diagnosis response."""

    def complete_diagnosis(self, request: ModelDiagnosisRequest) -> str:
        """Return JSON conforming to OpenARIA's DiagnosisResult schema."""
