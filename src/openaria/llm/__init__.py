"""Provider-neutral model assistance interfaces for OpenARIA."""

from .gateway import ModelAssistanceConfig, ModelDiagnosisRequest, ModelGateway
from .service import diagnose_with_optional_model

__all__ = [
    "ModelAssistanceConfig",
    "ModelDiagnosisRequest",
    "ModelGateway",
    "diagnose_with_optional_model",
]
