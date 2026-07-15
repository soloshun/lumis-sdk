"""Bounded, cookbook-owned tools used by the software-delivery demonstration agent."""

from pathlib import Path
from typing import Literal, TypeAlias

import httpx
from agno.tools import Toolkit

from lumis_sdk.adapters.deterministic import diagnose_text
from lumis_sdk.adapters.incidents import incident_from_log
from lumis_sdk.adapters.reports import render_markdown_report
from lumis_sdk.adapters.sqlite import SQLiteIncidentStore
from lumis_sdk.config import LumisConfig, resolve_project_path
from lumis_sdk.domain import DiagnosisResult
from lumis_sdk.security import redact_value

DeliveryIncidentId: TypeAlias = Literal[
    "lockfile-ci-001", "workflow-permission-001", "infra-resource-001"
]
DeliveryContextName: TypeAlias = Literal["logs", "metrics", "lineage", "verification"]
DeliveryRunbookName: TypeAlias = Literal[
    "ci-permission-investigation", "infrastructure-reference-investigation"
]
DeliveryPlaybookName: TypeAlias = Literal["dependency_lockfile_refresh"]
DeliveryCodePath: TypeAlias = Literal[
    ".github/workflows/release.yml", "infra/main.tf", "src/checkout.py"
]


class SoftwareDeliveryTools(Toolkit):
    """A reusable Agno toolkit with bounded delivery-investigation capabilities.

    Only the methods explicitly passed to ``Toolkit`` are exposed to an agent. Local helpers such
    as ``diagnosis_for`` stay available to this cookbook's deterministic runner, not the agent.
    """

    def __init__(self, base_url: str, config_path: Path, config: LumisConfig) -> None:
        """Create the toolkit and register its intentional, recommendation-only tool surface."""
        self.base_url = base_url
        self.config_path = config_path
        self.config = config
        super().__init__(
            name="software_delivery_investigation",
            tools=[
                self.get_incident,
                self.get_investigation_guide,
                self.get_context,
                self.get_framework_diagnosis,
                self.read_runbook,
                self.read_playbook,
                self.read_synthetic_project_file,
                self.propose_playbook,
                self.request_approval,
                self.export_analysis,
            ],
        )

    def get_incident(self, incident_id: DeliveryIncidentId) -> dict[str, object]:
        """Retrieve the normalized synthetic delivery incident by its ID."""
        return self._mapping(self._get(f"/incidents/{incident_id}"))

    def get_investigation_guide(self, incident_id: DeliveryIncidentId) -> dict[str, object]:
        """Discover the exact context, code, runbook, and playbook names for this incident.

        Retrieve this guide before requesting detailed evidence. Use only its returned identifiers;
        do not guess file paths, context names, or knowledge-document names.
        """
        return self._mapping(self._get(f"/incidents/{incident_id}/guide"))

    def get_context(
        self, incident_id: DeliveryIncidentId, context_name: DeliveryContextName
    ) -> object:
        """Retrieve one named delivery context item listed in the investigation guide."""
        return self._get(f"/incidents/{incident_id}/context/{context_name}")

    def get_framework_diagnosis(self, incident_id: DeliveryIncidentId) -> dict[str, object]:
        """Run the cookbook's deterministic Lumis SDK rules over the synthetic logs."""
        return self.diagnosis_for(incident_id).model_dump(mode="json")

    def read_runbook(self, name: DeliveryRunbookName) -> dict[str, str]:
        """Read one valid CI or infrastructure runbook named by the investigation guide."""
        return self._string_mapping(self._get(f"/knowledge/runbooks/{name}"))

    def read_playbook(self, name: DeliveryPlaybookName) -> dict[str, str]:
        """Read the one allowlisted, recommendation-only delivery playbook."""
        return self._string_mapping(self._get(f"/knowledge/playbooks/{name}"))

    def read_synthetic_project_file(self, file_path: DeliveryCodePath) -> dict[str, str]:
        """Read one valid project file named by the investigation guide."""
        return self._string_mapping(self._get(f"/code/{file_path}"))

    def record_framework_diagnosis(self, incident_id: DeliveryIncidentId) -> dict[str, str]:
        """Save a deterministic framework diagnosis to local SQLite memory."""
        stored = self._save_report(
            incident_id,
            report_name=f"{incident_id}.md",
            report=self._deterministic_report(incident_id),
        )
        return {
            "incident_id": stored.id,
            "source_incident_id": incident_id,
            "report_path": stored.report_path,
        }

    def propose_playbook(self, incident_id: DeliveryIncidentId) -> dict[str, object]:
        """Return the configured playbook recommendation without executing it."""
        diagnosis = self.diagnosis_for(incident_id)
        return {
            "playbook": diagnosis.suggested_playbook,
            "execution_allowed": False,
            "approval_required": True,
        }

    def request_approval(self, incident_id: DeliveryIncidentId) -> dict[str, str]:
        """Describe the human approval boundary; this tool cannot approve a change."""
        return {
            "incident_id": incident_id,
            "status": "pending_human_approval",
            "reason": "Workflow, release, permission, and infrastructure changes need approval.",
        }

    def export_analysis(
        self, incident_id: DeliveryIncidentId, report_name: str, markdown: str
    ) -> dict[str, str]:
        """Create one named Markdown report from the complete final analysis.

        Use a simple `.md` filename such as `workflow-permission-001-llm.md`.
        Never use a directory path.
        Pass the full human-readable report as `markdown`, not a placeholder or summary.
        """
        candidate = Path(report_name)
        if candidate.name != report_name or candidate.suffix != ".md":
            raise ValueError("report_name must be a simple Markdown filename ending in .md")
        stored = self._save_report(
            incident_id,
            report_name=report_name,
            report=markdown,
        )
        return {"report_path": stored.report_path, "incident_id": stored.id}

    def diagnosis_for(self, incident_id: str) -> DiagnosisResult:
        """Return the deterministic diagnosis used before any optional model call."""
        return diagnose_text(self.log_text_for(incident_id), self.config.rules)

    def log_text_for(self, incident_id: str) -> str:
        """Normalize the synthetic log context into text for the deterministic engine."""
        logs = self.get_context(incident_id, "logs")
        return "\n".join(logs) if isinstance(logs, list) else str(logs)

    def _deterministic_report(self, incident_id: str) -> str:
        """Render the deterministic report used for known incident signatures."""
        log_text = self.log_text_for(incident_id)
        incident = incident_from_log(log_text, f"fastapi://{incident_id}/logs", self.config.project)
        return render_markdown_report(incident, self.diagnosis_for(incident_id))

    def _save_report(self, incident_id: str, *, report_name: str, report: str):
        """Write one local report and create its matching SQLite incident record."""
        log_text = self.log_text_for(incident_id)
        incident = incident_from_log(log_text, f"fastapi://{incident_id}/logs", self.config.project)
        report_path = self._path(self.config.reports.output_dir) / report_name
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        return SQLiteIncidentStore(self._path(self.config.memory.path)).save(
            incident,
            self.diagnosis_for(incident_id),
            report,
            report_path,
        )

    def _get(self, path: str) -> object:
        """Fetch and redact one response from the cookbook's read-only demo service."""
        response = httpx.get(f"{self.base_url.rstrip('/')}{path}", timeout=10.0)
        response.raise_for_status()
        return redact_value(response.json())

    def _path(self, configured_path: str) -> Path:
        """Resolve a local state path from the cookbook's Lumis SDK configuration."""
        return resolve_project_path(self.config_path, configured_path)

    @staticmethod
    def _mapping(value: object) -> dict[str, object]:
        """Return a JSON response as a dictionary for an agent tool result."""
        if not isinstance(value, dict):
            raise TypeError("The synthetic service returned an unexpected non-object response.")
        return {str(key): item for key, item in value.items()}

    def _string_mapping(self, value: object) -> dict[str, str]:
        """Return a redacted JSON object with string values for code and knowledge tools."""
        return {str(key): str(item) for key, item in self._mapping(value).items()}
