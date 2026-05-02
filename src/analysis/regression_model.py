from __future__ import annotations

from dataclasses import dataclass

import numpy as np  # type: ignore[import-untyped]


@dataclass
class ForecastPoint:
    index: int
    value: float


class RegressionForecaster:
    """Linear regression forecaster using numpy least-squares."""

    def predict_next(self, series: list[float], steps: int = 3) -> list[ForecastPoint]:
        if steps <= 0:
            return []
        if not series:
            return [ForecastPoint(index=i, value=0.0) for i in range(steps)]
        if len(series) == 1:
            return [ForecastPoint(index=1 + i, value=series[0]) for i in range(steps)]

        x = np.arange(len(series), dtype=float)
        y = np.array(series, dtype=float)

        # Ordinary least-squares: fit degree-1 polynomial
        coeffs = np.polyfit(x, y, deg=1)
        slope, intercept = float(coeffs[0]), float(coeffs[1])

        start = len(series)
        return [
            ForecastPoint(
                index=start + i,
                value=float(f"{slope * (start + i) + intercept:.2f}"),
            )
            for i in range(steps)
        ]
