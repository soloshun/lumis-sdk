"""Tiny dependency-free training fixture for the ML cookbook; not a production model."""

import csv
from pathlib import Path


def fit_area_only_regression(rows: list[dict[str, str]]) -> tuple[float, float]:
    """Fit y = intercept + slope * area_sq_m using ordinary least squares."""
    areas = [float(row["area_sq_m"]) for row in rows]
    prices = [float(row["price_thousands"]) for row in rows]
    mean_area = sum(areas) / len(areas)
    mean_price = sum(prices) / len(prices)
    numerator = sum((area - mean_area) * (price - mean_price) for area, price in zip(areas, prices))
    denominator = sum((area - mean_area) ** 2 for area in areas)
    slope = numerator / denominator
    return mean_price - slope * mean_area, slope


if __name__ == "__main__":
    dataset = Path(__file__).parents[1] / "data" / "housing_train.csv"
    with dataset.open(newline="", encoding="utf-8") as handle:
        intercept, slope = fit_area_only_regression(list(csv.DictReader(handle)))
    print(f"synthetic area-only model: price = {intercept:.2f} + {slope:.2f} * area_sq_m")
