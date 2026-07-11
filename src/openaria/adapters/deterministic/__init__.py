"""Reference deterministic diagnosis adapter."""

from .engine import (
    DeterministicDiagnosis,
    RuleMatch,
    diagnose_text,
    diagnose_text_with_explanation,
)

__all__ = [
    "DeterministicDiagnosis",
    "RuleMatch",
    "diagnose_text",
    "diagnose_text_with_explanation",
]
