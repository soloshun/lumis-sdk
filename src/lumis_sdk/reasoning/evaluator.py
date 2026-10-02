"""Three-valued hypothesis checks over facts, not model-authored evidence links."""

from lumis_sdk.core import Check, Evidence, Hypothesis, HypothesisAssessment, IncidentContext


def _compare(check: Check, evidence: Evidence) -> bool | None:
    actual, expected = evidence.value, check.value
    if check.operator in {"eq", "ne"}:
        # Python's True == 1 must not turn a health flag into a numeric metric.
        if isinstance(actual, bool) != isinstance(expected, bool):
            return None
        if isinstance(actual, str) != isinstance(expected, str):
            return None
        return (actual == expected) if check.operator == "eq" else (actual != expected)
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return None
    if isinstance(expected, bool) or not isinstance(expected, (int, float)):
        return None
    if check.operator == "gt":
        return actual > expected
    if check.operator == "ge":
        return actual >= expected
    if check.operator == "lt":
        return actual < expected
    return actual <= expected


def assess(
    hypothesis: Hypothesis, context: IncidentContext, sources: tuple[str, ...]
) -> HypothesisAssessment:
    """Contradiction dominates support; missing, degraded, or conflicting facts stay unknown.

    Each prediction must be true and each falsifier false to count as supported. This is a
    deterministic operational test, not formal causal proof or a calibrated posterior.
    """
    support: set[str] = set()
    contradiction: set[str] = set()
    missing: list[Check] = []
    for falsifier, checks in ((False, hypothesis.predictions), (True, hypothesis.falsifiers)):
        for check in checks:
            observations = tuple(
                item
                for item in context.evidence
                if item.entity_id == check.entity_id
                and item.key == check.key
                and item.quality == "observed"
            )
            values = [_compare(check, item) for item in observations]
            known = {value for value in values if value is not None}
            if len(known) != 1 or any(value is None for value in values):
                missing.append(check)
                continue
            passed = next(iter(known))
            target = contradiction if passed == falsifier else support
            target.update(item.id for item in observations)
    return HypothesisAssessment(
        hypothesis=hypothesis,
        sources=sources,
        state="contradicted" if contradiction else "unresolved" if missing else "supported",
        supporting_evidence_ids=tuple(sorted(support)),
        contradicting_evidence_ids=tuple(sorted(contradiction)),
        missing_checks=tuple(missing),
    )
