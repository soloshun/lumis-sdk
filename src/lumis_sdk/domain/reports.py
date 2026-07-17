"""Versioned machine-readable diagnosis report contracts."""

from typing import Literal

from pydantic import ConfigDict, Field

from .models import DiagnosisResult, DomainModel, IncidentInput, TruthState

DIAGNOSIS_REPORT_API_VERSION: Literal["lumis.dev/v1"] = "lumis.dev/v1"
DIAGNOSIS_REPORT_KIND: Literal["DiagnosisReport"] = "DiagnosisReport"


class DiagnosisReportDocument(DomainModel):
    """A stable JSON diagnosis report that preserves evidence and truth state."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_version: Literal["lumis.dev/v1", "lumis.dev/v1alpha1"] = Field(alias="apiVersion")
    kind: Literal["DiagnosisReport"] = DIAGNOSIS_REPORT_KIND
    incident: IncidentInput
    diagnosis: DiagnosisResult
    truth_state: TruthState = Field(default=TruthState.UNCONFIRMED_HYPOTHESIS, alias="truthState")
    confirmed_resolution: str | None = Field(default=None, alias="confirmedResolution")
