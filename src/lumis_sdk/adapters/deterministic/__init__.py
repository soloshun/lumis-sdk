"""Reference deterministic diagnosis adapter."""

from .engine import (
    DeterministicDiagnosis,
    RuleMatch,
    diagnose_text,
    diagnose_text_with_explanation,
)
from .structured import (
    ConditionEvaluation,
    StructuredDeterministicDiagnosis,
    StructuredRuleEvaluation,
    diagnose_structured,
    evaluate_diagnosis_rule,
)

__all__ = [
    "ConditionEvaluation",
    "DeterministicDiagnosis",
    "RuleMatch",
    "StructuredDeterministicDiagnosis",
    "StructuredRuleEvaluation",
    "diagnose_structured",
    "diagnose_text",
    "diagnose_text_with_explanation",
    "evaluate_diagnosis_rule",
]
