"""Explicit operator opt-in and resource bounds; no unsafe host execution fallback."""

from typing import Annotated, Self

from pydantic import Field, StrictBool, StringConstraints, model_validator

from lumis_sdk.core.contracts import Contract


class SandboxPolicy(Contract):
    enabled: StrictBool = False
    image: (
        Annotated[
            str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9./:_-]*@sha256:[a-f0-9]{64}$")
        ]
        | None
    ) = None
    timeout_seconds: float = Field(default=10, gt=0, le=60)
    memory_mb: int = Field(default=128, ge=64, le=512)
    cpus: float = Field(default=0.5, gt=0, le=2)
    pids: int = Field(default=32, ge=8, le=64)
    max_output_bytes: int = Field(default=8000, ge=100, le=64000)

    @model_validator(mode="after")
    def require_pinned_image(self) -> Self:
        if self.enabled and self.image is None:
            raise ValueError("sandbox requires an explicitly approved digest-pinned Python image")
        return self
