"""Synthetic inference contract used only by the feature-contract incident."""

REQUIRED_FEATURES = ("rooms", "area_sq_m", "income")


def predict(feature_row: dict[str, float]) -> float:
    """Return a toy score after enforcing the model's feature contract."""
    missing = [feature for feature in REQUIRED_FEATURES if feature not in feature_row]
    if missing:
        raise ValueError(f"expected 3 features but received {len(feature_row)}; missing={missing}")
    return (
        30.0 * feature_row["rooms"] + 1.9 * feature_row["area_sq_m"] + 0.001 * feature_row["income"]
    )
