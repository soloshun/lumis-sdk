"""Non-rejecting authoring diagnostics; mechanical assessment remains unchanged."""

from lumis_sdk.core.contracts import Check, Hypothesis


def numeric_overlap(left: Check, right: Check) -> bool:
    if (left.entity_id, left.key) != (right.entity_id, right.key):
        return False
    if any(
        isinstance(c.value, bool) or not isinstance(c.value, (int, float)) for c in (left, right)
    ):
        return False
    lower: tuple[int | float, bool] | None = None
    upper: tuple[int | float, bool] | None = None
    excluded: set[int | float] = set()
    for check in (left, right):
        value = check.value
        assert isinstance(value, (int, float))
        if check.operator in {"gt", "ge", "eq"}:
            bound = (value, check.operator != "gt")
            if lower is None or bound[0] > lower[0]:
                lower = bound
            elif bound[0] == lower[0]:
                lower = (value, lower[1] and bound[1])
        if check.operator in {"lt", "le", "eq"}:
            bound = (value, check.operator != "lt")
            if upper is None or bound[0] < upper[0]:
                upper = bound
            elif bound[0] == upper[0]:
                upper = (value, upper[1] and bound[1])
        if check.operator == "ne":
            excluded.add(value)
    if lower is None or upper is None or lower[0] < upper[0]:
        return True
    return lower[0] == upper[0] and lower[1] and upper[1] and lower[0] not in excluded


def hypothesis_warnings(hypothesis: Hypothesis) -> tuple[str, ...]:
    warnings = tuple(
        f"{hypothesis.id}: prediction {i + 1} and falsifier {j + 1} can both pass "
        f"for {prediction.entity_id}/{prediction.key}."
        for i, prediction in enumerate(hypothesis.predictions)
        for j, falsifier in enumerate(hypothesis.falsifiers)
        if numeric_overlap(prediction, falsifier)
    )
    if len(warnings) > 20:
        return (*warnings[:20], f"{len(warnings) - 20} further overlap warnings omitted.")
    return warnings
