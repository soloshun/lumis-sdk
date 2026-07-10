"""Run an opt-in Agno/OpenRouter investigation over the synthetic FastAPI estate."""

import os
from pathlib import Path

import httpx

from openaria.config import load_config
from openaria.incidents import incident_from_log
from openaria.memory import SQLiteIncidentStore
from openaria.reports import render_markdown_report
from openaria.triage import diagnose_text


def build_agent(base_url: str, model_id: str):
    """Build the cookbook agent only when its optional dependencies are installed."""
    from agno.agent import Agent
    from agno.models.openrouter import OpenRouter

    project_config = load_config(Path(__file__).with_name("openaria.yml"))
    cookbook_dir = Path(__file__).parent

    def get_incident(incident_id: str) -> dict[str, object]:
        """Retrieve the normalized synthetic incident by its ID."""
        return _get_json(base_url, f"/incidents/{incident_id}")

    def get_context(incident_id: str, context_name: str) -> object:
        """Retrieve one synthetic context item from the bounded demo service."""
        return _get_json(base_url, f"/incidents/{incident_id}/context/{context_name}")

    def get_framework_diagnosis(incident_id: str) -> dict[str, object]:
        """Run the OpenARIA configured deterministic diagnosis over the synthetic logs."""
        logs = get_context(incident_id, "logs")
        log_text = "\n".join(logs) if isinstance(logs, list) else str(logs)
        return diagnose_text(log_text, project_config.rules).model_dump(mode="json")

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
        report_path = cookbook_dir / project_config.reports.output_dir / f"{incident_id}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        memory_path = cookbook_dir / project_config.memory.path
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

    return Agent(
        model=OpenRouter(id=model_id),
        tools=[
            get_incident,
            get_context,
            get_framework_diagnosis,
            record_framework_diagnosis,
            propose_playbook,
            request_approval,
        ],
        instructions=[
            "Investigate only the supplied synthetic incident.",
            (
                "Call get_incident and get_framework_diagnosis, then retrieve schema, lineage, "
                "runbook, playbook, and verification."
            ),
            (
                "Call record_framework_diagnosis to write the validated diagnosis "
                "to local OpenARIA memory."
            ),
            (
                "Call propose_playbook and request_approval. Approval remains pending; "
                "never claim execution."
            ),
            "Separate confirmed facts from hypotheses and state missing evidence.",
            "Propose only the provided playbook. Do not claim to execute it.",
            "State that approval is required before any schema-related change.",
        ],
        markdown=True,
    )


def _get_json(base_url: str, path: str) -> object:
    response = httpx.get(f"{base_url.rstrip('/')}{path}", timeout=10.0)
    response.raise_for_status()
    return response.json()


def main() -> None:
    """Start a one-shot agent investigation after explicit user configuration."""
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit("Set OPENROUTER_API_KEY before running the live cookbook agent.")

    base_url = os.getenv("OPENARIA_DEMO_URL", "http://127.0.0.1:8000")
    model_id = os.getenv("OPENARIA_DEMO_MODEL", "openai/gpt-4o-mini")
    agent = build_agent(base_url, model_id)
    agent.print_response(
        "Investigate synthetic incident schema-drift-001 and produce a concise incident report.",
        stream=True,
    )


if __name__ == "__main__":
    main()
