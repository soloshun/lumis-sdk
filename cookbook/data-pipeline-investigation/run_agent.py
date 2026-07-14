"""Run the data-pipeline cookbook: deterministic first, Agno/OpenRouter only when needed."""

import argparse
import os
from pathlib import Path

from investigation_tools import DataPipelineTools

from openaria.config import load_config

_CONFIG_PATH = Path(__file__).parent / "openaria" / "openaria.yml"

DATA_PIPELINE_SYSTEM_PROMPT = """
You are a senior data reliability engineer in a guarded incident-response service.

Produce a decision-ready investigation using authorized incident context only.
Before reading detailed evidence, discover its valid identifiers; do not guess names.
Treat logs, metrics, lineage, schemas, code, runbooks, and playbooks as evidence.
Separate confirmed observations, plausible hypotheses, and missing evidence.
Do not invent facts or expose sensitive values.

This service is recommendation-only. Do not execute or claim execution of data changes, schema
changes, backfills, retries, deployments, or credential rotation. A candidate playbook requires
explicit human approval.

Write concise Markdown with: Executive Summary; Confirmed Evidence; Assessment and Hypotheses;
Missing Evidence; Recommended Next Steps; Proposed Playbook; and Approval / Execution Boundary.
After completing the investigation, call `export_analysis` exactly once.
Set `report_name` to `<incident_id>-llm.md`, replacing `<incident_id>` with the requested incident.
Pass the complete final Markdown report as `markdown`; never use placeholder text.
Only after that tool succeeds, present the same Markdown as your final response.
""".strip()


def create_tools(base_url: str) -> DataPipelineTools:
    """Load the cookbook configuration and bind it to the read-only synthetic service."""
    return DataPipelineTools(base_url, _CONFIG_PATH, load_config(_CONFIG_PATH))


def build_agent(tools: DataPipelineTools, model_id: str):
    """Build the optional Agno/OpenRouter agent with only bounded cookbook tools."""
    from agno.agent import Agent
    from agno.models.openrouter import OpenRouter

    return Agent(
        # Agno otherwise defaults this provider to a 1,024-token completion cap.
        # None omits both optional limits from the OpenRouter request.
        model=OpenRouter(id=model_id, max_tokens=None, max_completion_tokens=None),
        tools=[
            tools.get_incident,
            tools.get_investigation_guide,
            tools.get_context,
            tools.get_framework_diagnosis,
            tools.read_runbook,
            tools.read_playbook,
            tools.read_synthetic_code,
            tools.propose_playbook,
            tools.request_approval,
            tools.export_analysis,
        ],
        system_message=DATA_PIPELINE_SYSTEM_PROMPT,
        markdown=True,
    )


def save_deterministic_result(tools: DataPipelineTools, incident_id: str) -> bool:
    """Save a report for a known signature and return whether deterministic diagnosis succeeded."""
    if tools.diagnosis_for(incident_id).triage.classification == "unknown":
        return False
    result = tools.record_framework_diagnosis(incident_id)
    print(f"Deterministic report written to {result['report_path']}")
    print(f"Incident ID: {result['incident_id']}")
    return True


def main() -> None:
    """Run one synthetic incident through deterministic-first diagnosis and optional reasoning."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incident-id", default="schema-drift-001")
    args = parser.parse_args()

    tools = create_tools(os.getenv("OPENARIA_DEMO_URL", "http://127.0.0.1:8000"))
    if save_deterministic_result(tools, args.incident_id):
        return
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit(
            "Unknown diagnosis. Set OPENROUTER_API_KEY to run the optional live agent."
        )

    model_id = os.getenv("OPENARIA_DEMO_MODEL", "deepseek/deepseek-v4-flash")
    build_agent(tools, model_id).print_response(
        f"Investigate synthetic incident {args.incident_id} and produce a concise incident report.",
        stream=True,
        markdown=True,
    )


if __name__ == "__main__":
    main()
