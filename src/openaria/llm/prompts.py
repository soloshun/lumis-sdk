"""Prompts used by optional model adapters."""

from openaria.llm.gateway import ModelDiagnosisRequest


def build_diagnosis_request(redacted_log: str) -> ModelDiagnosisRequest:
    """Build a minimal diagnosis request from already-redacted context."""
    prompt = """You are the OpenARIA Diagnosis Agent.

Produce JSON that conforms to the OpenARIA DiagnosisResult schema.

Rules:
- Use only the supplied redacted log.
- Do not invent facts.
- Keep confirmed_facts separate from root_cause_hypothesis.
- Cite supplied log observations in evidence.
- Set confidence from 0 to 1 and list missing evidence.
- Recommend safe investigation steps only.
- Do not recommend or execute production actions.
"""
    return ModelDiagnosisRequest(prompt=prompt, redacted_log=redacted_log)
