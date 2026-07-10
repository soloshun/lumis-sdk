"""Run an opt-in Agno/OpenRouter investigation over synthetic ML incidents."""

import argparse
import os
from pathlib import Path

import httpx

from openaria.config import load_config, resolve_project_path
from openaria.incidents import incident_from_log
from openaria.llm import redact_value
from openaria.memory import SQLiteIncidentStore
from openaria.reports import render_markdown_report
from openaria.triage import diagnose_text

_COOKBOOK_DIR = Path(__file__).parent
_CONFIG_PATH = _COOKBOOK_DIR / "openaria" / "openaria.yml"
ML_REGRESSION_SYSTEM_PROMPT = "\n".join(
    (
        "You are a senior machine-learning reliability engineer in a guarded response service.",
        "Produce a decision-ready investigation for the requested ML pipeline incident.",
        "",
        "Work from authorized incident context only.",
        "Treat monitoring signals, metrics, feature contracts, lineage, artifacts, code, runbooks,",
        "and playbooks as evidence with different strengths.",
        "Use available capabilities selectively; do not follow a fixed tool sequence.",
        "Do not invent information that was not retrieved.",
        "",
        "Separate confirmed observations, plausible hypotheses, and missing evidence.",
        "A drift signal does not by itself prove model harm.",
        "A validation regression does not by itself identify the cause.",
        "State the metric, baseline, threshold, population, and evidence gaps when relevant.",
        "Do not expose unredacted sensitive data or use external knowledge as incident evidence.",
        "",
        "This service is recommendation-only.",
        "Do not retrain, promote, roll back, deploy, alter features, or change thresholds.",
        "Do not claim that any of those actions occurred.",
        "Candidate playbooks require human approval for model, data, or threshold changes.",
        "",
        "Produce concise Markdown with: Executive Summary; Confirmed Evidence; Assessment and",
        "Hypotheses; Missing Evidence; Recommended Next Steps; Proposed Playbook; and",
        "Approval / Execution Boundary.",
        "For an investigation requiring model reasoning, persist the final report through the",
        "available report-recording capability before completing the investigation.",
    )
)


def build_agent(base_url: str, model_id: str):
    """Build the cookbook agent only when optional dependencies are installed."""
    from agno.agent import Agent
    from agno.models.openrouter import OpenRouter

    project_config = load_config(_CONFIG_PATH)

    def get_incident(incident_id: str) -> dict[str, object]:
        """Retrieve the normalized synthetic ML incident by ID."""
        incident = redact_value(_get_json(base_url, f"/incidents/{incident_id}"))
        assert isinstance(incident, dict)
        return incident

    def get_context(incident_id: str, context_name: str) -> object:
        """Retrieve one bounded synthetic telemetry or metadata item."""
        return redact_value(_get_json(base_url, f"/incidents/{incident_id}/context/{context_name}"))

    def get_framework_diagnosis(incident_id: str) -> dict[str, object]:
        """Run the configured OpenARIA deterministic diagnosis over synthetic logs."""
        return _diagnosis_for(incident_id, get_context, project_config).model_dump(mode="json")

    def read_runbook(name: str) -> dict[str, str]:
        """Read one bounded synthetic ML investigation runbook."""
        knowledge = redact_value(_get_json(base_url, f"/knowledge/runbooks/{name}"))
        assert isinstance(knowledge, dict)
        return {str(key): str(value) for key, value in knowledge.items()}

    def read_playbook(name: str) -> dict[str, str]:
        """Read one recommendation-only synthetic playbook."""
        knowledge = redact_value(_get_json(base_url, f"/knowledge/playbooks/{name}"))
        assert isinstance(knowledge, dict)
        return {str(key): str(value) for key, value in knowledge.items()}

    def read_synthetic_code(file_path: str) -> dict[str, str]:
        """Read one allowlisted synthetic model or data file."""
        code = redact_value(_get_json(base_url, f"/code/{file_path}"))
        assert isinstance(code, dict)
        return {str(key): str(value) for key, value in code.items()}

    def record_framework_diagnosis(incident_id: str) -> dict[str, str]:
        """Store the configured diagnosis in this cookbook's local SQLite memory."""
        incident_data = get_incident(incident_id)
        log_text = _log_text(get_context(incident_id, "logs"))
        incident = incident_from_log(
            log_text, f"fastapi://{incident_id}/logs", project_config.project
        )
        diagnosis = diagnose_text(log_text, project_config.rules)
        report = render_markdown_report(incident, diagnosis)
        report_path = _configured_path(project_config.reports.output_dir) / f"{incident_id}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        stored = SQLiteIncidentStore(_configured_path(project_config.memory.path)).save(
            incident, diagnosis, report, report_path
        )
        return {"incident_id": stored.id, "source_incident_id": str(incident_data["id"])}

    def propose_playbook(incident_id: str) -> dict[str, object]:
        """Return a recommendation only when the configured rule provides one."""
        diagnosis = get_framework_diagnosis(incident_id)
        return {
            "playbook": diagnosis.get("suggested_playbook"),
            "execution_allowed": False,
            "approval_required": True,
        }

    def request_approval(incident_id: str) -> dict[str, str]:
        """Describe the human approval boundary; this tool cannot approve a change."""
        return {
            "incident_id": incident_id,
            "status": "pending_human_approval",
            "reason": "Model, feature, and threshold changes require an explicit human decision.",
        }

    def export_analysis(incident_id: str, markdown: str) -> dict[str, str]:
        """Save final LLM Markdown analysis to local memory and a report file."""
        log_text = _log_text(get_context(incident_id, "logs"))
        incident = incident_from_log(
            log_text, f"fastapi://{incident_id}/logs", project_config.project
        )
        fallback_diagnosis = diagnose_text(log_text, project_config.rules)
        report_path = _configured_path(project_config.reports.output_dir) / f"{incident_id}-llm.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(markdown, encoding="utf-8")
        stored = SQLiteIncidentStore(_configured_path(project_config.memory.path)).save(
            incident, fallback_diagnosis, markdown, report_path
        )
        return {"report_path": str(report_path), "incident_id": stored.id}

    return Agent(
        model=OpenRouter(id=model_id),
        tools=[
            get_incident,
            get_context,
            get_framework_diagnosis,
            read_runbook,
            read_playbook,
            read_synthetic_code,
            record_framework_diagnosis,
            propose_playbook,
            request_approval,
            export_analysis,
        ],
        system_message=ML_REGRESSION_SYSTEM_PROMPT,
        markdown=True,
    )


def _get_json(base_url: str, path: str) -> object:
    response = httpx.get(f"{base_url.rstrip('/')}{path}", timeout=10.0)
    response.raise_for_status()
    return response.json()


def _log_text(logs: object) -> str:
    return "\n".join(logs) if isinstance(logs, list) else str(logs)


def _configured_path(configured_path: str) -> Path:
    """Resolve a cookbook-local path from the OpenARIA YAML file."""
    return resolve_project_path(_CONFIG_PATH, configured_path).resolve()


def _diagnosis_for(incident_id: str, get_context, project_config):
    """Return a configured diagnosis after retrieving redacted synthetic logs."""
    return diagnose_text(_log_text(get_context(incident_id, "logs")), project_config.rules)


def save_deterministic_result_if_matched(base_url: str, incident_id: str) -> bool:
    """Save and print a deterministic result, returning false only for unknown incidents."""
    project_config = load_config(_CONFIG_PATH)
    logs = redact_value(_get_json(base_url, f"/incidents/{incident_id}/context/logs"))
    log_text = _log_text(logs)
    diagnosis = diagnose_text(log_text, project_config.rules)
    if diagnosis.triage.classification == "unknown":
        return False
    incident = incident_from_log(log_text, f"fastapi://{incident_id}/logs", project_config.project)
    report = render_markdown_report(incident, diagnosis)
    report_path = _configured_path(project_config.reports.output_dir) / (
        f"{incident_id}-deterministic.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    stored = SQLiteIncidentStore(_configured_path(project_config.memory.path)).save(
        incident, diagnosis, report, report_path
    )
    print(f"Deterministic report written to {report_path}")
    print(f"Incident ID: {stored.id}")
    return True


def main() -> None:
    """Start one bounded ML incident investigation after explicit user configuration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident-id", default="feature-drift-001")
    args = parser.parse_args()
    base_url = os.getenv("OPENARIA_DEMO_URL", "http://127.0.0.1:8000")
    if save_deterministic_result_if_matched(base_url, args.incident_id):
        return
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit(
            "Deterministic diagnosis was unknown. Set OPENROUTER_API_KEY to run the live agent."
        )
    model_id = os.getenv("OPENARIA_DEMO_MODEL", "deepseek/deepseek-v4-flash")
    build_agent(base_url, model_id).print_response(
        f"Investigate synthetic incident {args.incident_id} and produce a concise incident report.",
        stream=True,
    )


if __name__ == "__main__":
    main()
