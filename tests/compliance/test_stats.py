"""The interval printed beside every AI-agent count."""

from __future__ import annotations

import pytest

from compliance.stats import interval_text, wilson


def test_a_perfect_count_is_not_a_certainty():
    lo, hi = wilson(20, 20)
    assert hi == 1.0 and 0.83 < lo < 0.85          # 20 of 20 still leaves room below


def test_known_values():
    assert interval_text(10, 20) == "0.30–0.70"
    assert interval_text(0, 20) == "0.00–0.16"


def test_the_interval_contains_the_observed_share_and_narrows_with_n():
    for k, n in [(3, 8), (18, 32), (35, 160)]:
        lo, hi = wilson(k, n)
        assert lo <= k / n <= hi
    assert (wilson(50, 100)[1] - wilson(50, 100)[0]) < (wilson(5, 10)[1] - wilson(5, 10)[0])


def test_nonsense_is_refused():
    with pytest.raises(ValueError):
        wilson(5, 4)
    assert wilson(0, 0) == (0.0, 1.0)
