"""Tiny application fixture used only to give the synthetic CI estate a code boundary."""


def calculate_total(amount: float, tax_rate: float) -> float:
    """Return a deterministic checkout total."""
    return amount * (1 + tax_rate)
