"""Run the ML cookbook: deterministic first, Agno/OpenRouter only when needed."""

import argparse
import os
from pathlib import Path

from investigation_tools import MLRegressionTools

from openaria.config import load_config

_CONFIG_PATH = Path(__file__).parent / "openaria" / "openaria.yml"

ML_REGRESSION_SYSTEM_PROMPT = """
You are a senior machine-learning reliability engineer in a guarded response service.

Produce a decision-ready investigation using authorized incident context only.
Before reading detailed evidence, discover its valid identifiers; do not guess names.
Treat monitoring signals, metrics, feature contracts, lineage, artifacts, code, runbooks,
and playbooks as evidence. Separate
confirmed observations, plausible hypotheses, and missing evidence. State metrics, baselines,
thresholds, populations, and evidence gaps when relevant; do not invent evidence.

This service is recommendation-only. Do not retrain, promote, roll back, deploy, alter features, or
change thresholds. A candidate playbook requires explicit human approval.

Write concise Markdown with: Executive Summary; Confirmed Evidence; Assessment and Hypotheses;
Missing Evidence; Recommended Next Steps; Proposed Playbook; and Approval / Execution Boundary.
After completing the investigation, call `export_analysis` exactly once.
Set `report_name` to `<incident_id>-llm.md`, replacing `<incident_id>` with the requested incident.
Pass the complete final Markdown report as `markdown`; never use placeholder text.
Only after that tool succeeds, present the same Markdown as your final response.
""".strip()


def create_tools(base_url: str) -> MLRegressionTools:
    """Load the cookbook configuration and bind it to the read-only synthetic service."""
    return MLRegressionTools(base_url, _CONFIG_PATH, load_config(_CONFIG_PATH))


def build_agent(tools: MLRegressionTools, model_id: str):
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
        system_message=ML_REGRESSION_SYSTEM_PROMPT,
        markdown=True,
    )


def save_deterministic_result(tools: MLRegressionTools, incident_id: str) -> bool:
    """Save a report for a known signature and return whether deterministic diagnosis succeeded."""
    if tools.diagnosis_for(incident_id).triage.classification == "unknown":
        return False
    result = tools.record_framework_diagnosis(incident_id)
    print(f"Deterministic report written to {result['report_path']}")
    print(f"Incident ID: {result['incident_id']}")
    return True


def main() -> None:
    """Run one synthetic ML incident through deterministic-first diagnosis and optional reasoning.

    The optional model path is used only after the configured deterministic rules return unknown.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incident-id", default="feature-drift-001")
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
