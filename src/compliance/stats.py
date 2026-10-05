"""How much a count out of a handful of runs can be trusted.

The AI-agent figures are counts over a few runs -- trap runs held out of 20,
repeats that reproduced the first decision out of 32. A count is a sample, and
the report states its uncertainty beside it rather than leaving the reader to
guess.

The interval is Wilson's score interval for a binomial proportion, the usual
choice at small n and at proportions near 0 or 1, where the textbook normal
interval collapses to a point (20 of 20 is not a certainty of 1.00). It treats
every run as independent. Runs share a task, and a model tends to treat one
task the same way each time, so the honest interval is somewhat wider than
this; the report says so where it prints one.
"""

from __future__ import annotations

from math import sqrt

Z_95 = 1.959964


def wilson(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """95% Wilson score interval for ``k`` successes in ``n`` trials."""

    if n <= 0:
        return (0.0, 1.0)
    if not 0 <= k <= n:
        raise ValueError(f"k={k} is not between 0 and n={n}")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def interval_text(k: int, n: int) -> str:
    """'0.84-1.00' -- the interval as the tables print it."""

    lo, hi = wilson(k, n)
    return f"{lo:.2f}–{hi:.2f}"


__all__ = ["wilson", "interval_text", "Z_95"]
