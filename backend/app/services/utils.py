from __future__ import annotations


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def round4(value: float) -> float:
    return round(float(value), 4)
