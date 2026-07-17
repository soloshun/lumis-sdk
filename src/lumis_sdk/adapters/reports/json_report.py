"""Versioned JSON diagnosis report adapter."""

from pathlib import Path

from lumis_sdk.domain import (
    DIAGNOSIS_REPORT_API_VERSION,
    DiagnosisReportDocument,
    DiagnosisResult,
    IncidentInput,
    TruthState,
)


class JsonReportWriter:
    """Persist strict machine-readable diagnosis reports."""

    def write(
        self,
        *,
        incident: IncidentInput,
        diagnosis: DiagnosisResult,
        destination: Path,
    ) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            render_json_report(incident, diagnosis),
            encoding="utf-8",
        )
        return destination


def render_json_report(
    incident: IncidentInput,
    diagnosis: DiagnosisResult,
    *,
    truth_state: TruthState = TruthState.UNCONFIRMED_HYPOTHESIS,
    confirmed_resolution: str | None = None,
) -> str:
    """Render one strict, machine-readable diagnosis report."""
    document = DiagnosisReportDocument(
        apiVersion=DIAGNOSIS_REPORT_API_VERSION,
        kind="DiagnosisReport",
        incident=incident,
        diagnosis=diagnosis,
        truthState=truth_state,
        confirmedResolution=confirmed_resolution,
    )
    return document.model_dump_json(by_alias=True, indent=2) + "\n"


def parse_json_report(value: str) -> DiagnosisReportDocument:
    """Validate and return one versioned JSON diagnosis report."""
    return DiagnosisReportDocument.model_validate_json(value)


def diagnosis_report_json_schema() -> dict[str, object]:
    """Return the JSON Schema used by editors and downstream tooling."""
    return _report_schema(DIAGNOSIS_REPORT_API_VERSION)


def legacy_diagnosis_report_json_schema() -> dict[str, object]:
    """Return the frozen deprecated diagnosis-report schema."""
    return _report_schema("lumis.dev/v1alpha1")


def _report_schema(version: str) -> dict[str, object]:
    schema = DiagnosisReportDocument.model_json_schema(by_alias=True)
    marker = schema["properties"]["apiVersion"]
    assert isinstance(marker, dict)
    marker.pop("enum", None)
    marker["const"] = version
    return schema
