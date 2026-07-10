"""Synthetic code used only by the unfamiliar-incident cookbook scenario."""


def calculate_adjusted_close(record: dict[str, float]) -> float:
    """Return an adjusted price from a source record."""
    return record["adjusted_close"] * 0.99
