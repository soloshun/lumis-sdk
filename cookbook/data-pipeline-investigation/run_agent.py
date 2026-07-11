"""Run an opt-in Agno/OpenRouter investigation over the synthetic FastAPI estate."""

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

DATA_PIPELINE_SYSTEM_PROMPT = "\n".join(
    (
        "You are a senior data reliability engineer in a guarded incident-response service.",
        "Produce a decision-ready investigation for the requested data-pipeline incident.",
        "",
        "Work from authorized incident context only.",
        "Treat logs, metrics, lineage, schemas, code, runbooks, and playbooks as evidence.",
        "Do not infer facts that the evidence does not support.",
        "Use available capabilities selectively to reduce material uncertainty.",
        "Do not mention internal tool mechanics unless they are relevant evidence.",
        "",
        "Separate confirmed observations, plausible root-cause hypotheses, and missing evidence.",
        "If evidence is insufficient, say so plainly and recommend the next safest step.",
        "Do not use external knowledge, invent telemetry, or expose unredacted sensitive data.",
        "A rule match is evidence, not proof of a root cause.",
        "",
        "This service is recommendation-only.",
        "Do not execute or imply execution of data changes, schema changes, backfills, retries,",
        "deployments, credential rotation, or other remediation.",
        "A playbook is a candidate recommendation; consequential changes need human approval.",
        "",
        "Produce concise Markdown with: Executive Summary; Confirmed Evidence; Assessment and",
        "Hypotheses; Missing Evidence; Recommended Next Steps; Proposed Playbook; and",
        "Approval / Execution Boundary.",
        "For an investigation requiring model reasoning, persist the final report through the",
        "available report-recording capability before completing the investigation.",
    )
)


def build_agent(base_url: str, model_id: str):
    """Build the cookbook agent only when its optional dependencies are installed."""
    from agno.agent import Agent
    from agno.models.openrouter import OpenRouter

    config_path = Path(__file__).parent / "openaria" / "openaria.yml"
    project_config = load_config(config_path)

    def get_incident(incident_id: str) -> dict[str, object]:
        """Retrieve the normalized synthetic incident by its ID."""
        incident = redact_value(_get_json(base_url, f"/incidents/{incident_id}"))
        assert isinstance(incident, dict)
        return incident

    def get_context(incident_id: str, context_name: str) -> object:
        """Retrieve one synthetic context item from the bounded demo service."""
        return redact_value(_get_json(base_url, f"/incidents/{incident_id}/context/{context_name}"))

    def get_framework_diagnosis(incident_id: str) -> dict[str, object]:
        """Run the OpenARIA configured deterministic diagnosis over the synthetic logs."""
        logs = get_context(incident_id, "logs")
        log_text = "\n".join(logs) if isinstance(logs, list) else str(logs)
        return diagnose_text(log_text, project_config.rules).model_dump(mode="json")

    def read_runbook(name: str) -> dict[str, str]:
        """Read one synthetic project runbook by name before recommending a change."""
        knowledge = redact_value(_get_json(base_url, f"/knowledge/runbooks/{name}"))
        assert isinstance(knowledge, dict)
        return {str(key): str(value) for key, value in knowledge.items()}

    def read_playbook(name: str) -> dict[str, str]:
        """Read one allowlisted synthetic playbook by name; it is recommendation-only."""
        knowledge = redact_value(_get_json(base_url, f"/knowledge/playbooks/{name}"))
        assert isinstance(knowledge, dict)
        return {str(key): str(value) for key, value in knowledge.items()}

    def read_synthetic_code(file_path: str) -> dict[str, str]:
        """Read one bounded synthetic code file for an unfamiliar incident."""
        code = redact_value(_get_json(base_url, f"/code/{file_path}"))
        assert isinstance(code, dict)
        return {str(key): str(value) for key, value in code.items()}

    def record_framework_diagnosis(incident_id: str) -> dict[str, str]:
        """Store the configured OpenARIA diagnosis in this cookbook's local SQLite memory."""
        incident_data = get_incident(incident_id)
        logs = get_context(incident_id, "logs")
        log_text = "\n".join(logs) if isinstance(logs, list) else str(logs)
        incident = incident_from_log(
            log_text, f"fastapi://{incident_id}/logs", project_config.project
        )
        diagnosis = diagnose_text(log_text, project_config.rules)
        report = render_markdown_report(incident, diagnosis)
        report_path = (
            _configured_path(config_path, project_config.reports.output_dir) / f"{incident_id}.md"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        memory_path = _configured_path(config_path, project_config.memory.path)
        stored = SQLiteIncidentStore(memory_path).save(incident, diagnosis, report, report_path)
        return {"incident_id": stored.id, "source_incident_id": str(incident_data["id"])}

    def propose_playbook(incident_id: str) -> dict[str, object]:
        """Return the configured recommendation-only playbook for the synthetic incident."""
        diagnosis = get_framework_diagnosis(incident_id)
        return {
            "playbook": diagnosis.get("suggested_playbook"),
            "execution_allowed": False,
            "approval_required": True,
        }

    def request_approval(incident_id: str) -> dict[str, str]:
        """Explain the required human approval boundary; this tool cannot approve an action."""
        return {
            "incident_id": incident_id,
            "status": "pending_human_approval",
            "reason": "Schema-related changes require an explicit human decision.",
        }

    def export_analysis(incident_id: str, markdown: str) -> dict[str, str]:
        """Save the final LLM Markdown analysis to local OpenARIA memory and a report file."""
        logs = get_context(incident_id, "logs")
        log_text = "\n".join(logs) if isinstance(logs, list) else str(logs)
        incident = incident_from_log(
            log_text, f"fastapi://{incident_id}/logs", project_config.project
        )
        fallback_diagnosis = diagnose_text(log_text, project_config.rules)
        report_path = (
            _configured_path(config_path, project_config.reports.output_dir)
            / f"{incident_id}-llm.md"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(markdown, encoding="utf-8")
        stored = SQLiteIncidentStore(
            _configured_path(config_path, project_config.memory.path)
        ).save(incident, fallback_diagnosis, markdown, report_path)
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
        system_message=DATA_PIPELINE_SYSTEM_PROMPT,
        markdown=True,
    )


def _get_json(base_url: str, path: str) -> object:
    response = httpx.get(f"{base_url.rstrip('/')}{path}", timeout=10.0)
    response.raise_for_status()
    return response.json()


def _configured_path(config_path: Path, configured_path: str) -> Path:
    """Resolve a cookbook-local path from its OpenARIA YAML file."""
    return resolve_project_path(config_path, configured_path).resolve()


def save_deterministic_result_if_matched(base_url: str, incident_id: str) -> bool:
    """Save and print a deterministic result, returning false only for unknown incidents."""
    cookbook_dir = Path(__file__).parent
    config_path = cookbook_dir / "openaria" / "openaria.yml"
    project_config = load_config(config_path)
    logs = redact_value(_get_json(base_url, f"/incidents/{incident_id}/context/logs"))
    log_text = "\n".join(logs) if isinstance(logs, list) else str(logs)
    diagnosis = diagnose_text(log_text, project_config.rules)
    if diagnosis.triage.classification == "unknown":
        return False

    incident = incident_from_log(log_text, f"fastapi://{incident_id}/logs", project_config.project)
    report = render_markdown_report(incident, diagnosis)
    report_path = _configured_path(config_path, project_config.reports.output_dir) / (
        f"{incident_id}-deterministic.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    stored = SQLiteIncidentStore(_configured_path(config_path, project_config.memory.path)).save(
        incident, diagnosis, report, report_path
    )
    print(f"Deterministic report written to {report_path}")
    print(f"Incident ID: {stored.id}")
    return True


def main() -> None:
    """Start a one-shot agent investigation after explicit user configuration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident-id", default="schema-drift-001")
    args = parser.parse_args()
    base_url = os.getenv("OPENARIA_DEMO_URL", "http://127.0.0.1:8000")
    if save_deterministic_result_if_matched(base_url, args.incident_id):
        return
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit(
            "Deterministic diagnosis was unknown. Set OPENROUTER_API_KEY to run the live agent."
        )
    model_id = os.getenv("OPENARIA_DEMO_MODEL", "deepseek/deepseek-v4-flash")
    agent = build_agent(base_url, model_id)
    agent.print_response(
        f"Investigate synthetic incident {args.incident_id} and produce a concise incident report.",
        stream=True,
    )


if __name__ == "__main__":
    main()
