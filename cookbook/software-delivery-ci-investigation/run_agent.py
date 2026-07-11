"""Run an opt-in Agno/OpenRouter investigation over synthetic CI incidents."""

import argparse
import os
from pathlib import Path

import httpx

from openaria.adapters.deterministic import diagnose_text
from openaria.adapters.incidents import incident_from_log
from openaria.adapters.reports import render_markdown_report
from openaria.adapters.sqlite import SQLiteIncidentStore
from openaria.config import load_config, resolve_project_path
from openaria.security import redact_value

_COOKBOOK_DIR = Path(__file__).parent
_CONFIG_PATH = _COOKBOOK_DIR / "openaria" / "openaria.yml"
SOFTWARE_DELIVERY_SYSTEM_PROMPT = "\n".join(
    (
        "You are a senior delivery reliability engineer in a guarded response service.",
        "Produce a decision-ready investigation for the requested delivery incident.",
        "",
        "Work from authorized incident context only.",
        "Treat CI logs, workflow files, code, infrastructure files, and runbooks as evidence.",
        "Use available capabilities selectively; do not follow a fixed tool sequence.",
        "Do not invent repository state, cloud state, permissions, or command output.",
        "",
        "Separate confirmed observations, plausible hypotheses, and missing evidence.",
        "A validation or authorization error does not prove the intended configuration.",
        "Do not expose unredacted sensitive data or use external knowledge as incident evidence.",
        "",
        "This service is recommendation-only.",
        "Do not modify code, workflows, permissions, infrastructure, or releases.",
        "Do not claim that any of those actions occurred.",
        "Candidate changes require explicit human approval and a reviewable change process.",
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
        """Retrieve the normalized synthetic software-delivery incident by ID."""
        incident = redact_value(_get_json(base_url, f"/incidents/{incident_id}"))
        assert isinstance(incident, dict)
        return incident

    def get_context(incident_id: str, context_name: str) -> object:
        """Retrieve one bounded synthetic CI or infrastructure context item."""
        return redact_value(_get_json(base_url, f"/incidents/{incident_id}/context/{context_name}"))

    def get_framework_diagnosis(incident_id: str) -> dict[str, object]:
        """Run configured OpenARIA deterministic diagnosis over the incident logs."""
        return diagnose_text(
            _log_text(get_context(incident_id, "logs")), project_config.rules
        ).model_dump(mode="json")

    def read_runbook(name: str) -> dict[str, str]:
        """Read one bounded synthetic CI or infrastructure investigation runbook."""
        knowledge = redact_value(_get_json(base_url, f"/knowledge/runbooks/{name}"))
        assert isinstance(knowledge, dict)
        return {str(key): str(value) for key, value in knowledge.items()}

    def read_playbook(name: str) -> dict[str, str]:
        """Read one recommendation-only synthetic software-delivery playbook."""
        knowledge = redact_value(_get_json(base_url, f"/knowledge/playbooks/{name}"))
        assert isinstance(knowledge, dict)
        return {str(key): str(value) for key, value in knowledge.items()}

    def read_synthetic_project_file(file_path: str) -> dict[str, str]:
        """Read one allowlisted synthetic workflow, source, or infrastructure file."""
        project_file = redact_value(_get_json(base_url, f"/code/{file_path}"))
        assert isinstance(project_file, dict)
        return {str(key): str(value) for key, value in project_file.items()}

    def record_framework_diagnosis(incident_id: str) -> dict[str, str]:
        """Store the configured framework diagnosis in local SQLite memory."""
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
            "reason": "Workflow, release, permission, and infrastructure changes need approval.",
        }

    def export_analysis(incident_id: str, markdown: str) -> dict[str, str]:
        """Persist final LLM Markdown analysis to local memory and a report file."""
        log_text = _log_text(get_context(incident_id, "logs"))
        incident = incident_from_log(
            log_text, f"fastapi://{incident_id}/logs", project_config.project
        )
        fallback = diagnose_text(log_text, project_config.rules)
        report_path = _configured_path(project_config.reports.output_dir) / f"{incident_id}-llm.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(markdown, encoding="utf-8")
        stored = SQLiteIncidentStore(_configured_path(project_config.memory.path)).save(
            incident, fallback, markdown, report_path
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
            read_synthetic_project_file,
            record_framework_diagnosis,
            propose_playbook,
            request_approval,
            export_analysis,
        ],
        system_message=SOFTWARE_DELIVERY_SYSTEM_PROMPT,
        markdown=True,
    )


def _get_json(base_url: str, path: str) -> object:
    response = httpx.get(f"{base_url.rstrip('/')}{path}", timeout=10.0)
    response.raise_for_status()
    return response.json()


def _configured_path(configured_path: str) -> Path:
    """Resolve a cookbook-local path from the OpenARIA YAML file."""
    return resolve_project_path(_CONFIG_PATH, configured_path)


def _log_text(logs: object) -> str:
    return "\n".join(logs) if isinstance(logs, list) else str(logs)


def save_deterministic_result_if_matched(base_url: str, incident_id: str) -> bool:
    """Save and print a deterministic report, returning false only for unknown incidents."""
    project_config = load_config(_CONFIG_PATH)
    log_text = _log_text(
        redact_value(_get_json(base_url, f"/incidents/{incident_id}/context/logs"))
    )
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
    """Start one bounded CI or infrastructure incident investigation."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident-id", default="lockfile-ci-001")
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
