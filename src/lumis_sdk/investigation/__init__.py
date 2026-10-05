"""Basic public investigator interfaces; optional model framework is imported lazily."""

from .contracts import AgentOutput, DiagnosticRule, HumanResolution, IncidentReport

__all__ = ["AgentOutput", "DiagnosticRule", "HumanResolution", "IncidentReport"]
