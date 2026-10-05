"""Uniform hypothesis sources and deterministic evidence evaluation."""

from .evaluator import assess
from .sources import HypothesisSource, MemoryHypothesisSource, ModelHypothesisSource, RuleSource

__all__ = [
    "HypothesisSource",
    "MemoryHypothesisSource",
    "ModelHypothesisSource",
    "RuleSource",
    "assess",
]
