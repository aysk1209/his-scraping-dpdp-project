"""Cost metering for an extraction run -- the benchmark's second axis.

Compliance scoring ranks techniques on one axis. This module supplies the other:
what a technique *costs* to run. The metrics that lead here are deterministic --
they reproduce on any machine and do not drift with dataset size or network
conditions -- because a benchmark a reader cannot reproduce is a weak benchmark.
Wall-clock time is reported beside them, but as a hardware-dependent secondary.

The measure that carries the argument is ``excess_ratio``: distinct fields pulled
divided by the fields the task's purpose actually requires. It is simultaneously
a cost measure and a compliance measure, because fields pulled beyond the purpose
*are* the overreach the data-minimisation rule penalises. Cost and compliance
turn out to be one quantity seen from two directions.

# DPDP Act 2023 -- data minimisation principle: personal data processed is
# limited to what is necessary for the specified purpose. ``excess_ratio``
# expresses that limit as a cost, and ``coverage`` stops a technique from
# scoring well by simply pulling nothing.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel

from extraction.base import HISDataSource
from interop.layers import HISLayer

# A single addressable data element: (HIS layer value, field name).
FieldRef = tuple[str, str]


def _ratio(numerator: int, denominator: int) -> float | None:
    """Rounded ratio, or None when the task declares no needed fields."""

    if denominator <= 0:
        return None
    return round(numerator / denominator, 3)


class ExtractionCost(BaseModel):
    """What one extraction run cost, in reproducible terms plus wall-clock."""

    fetches: int = 0              # fetch() calls (one per layer requested)
    page_loads: int | None = None # browser pages loaded, when the source is a portal
    records: int = 0              # rows returned
    fields_pulled: int = 0        # total field values returned (with repetition)
    distinct_fields: int = 0      # distinct (layer, field) pairs touched
    needed_fields: int = 0        # distinct pairs the task declares as necessary
    matched_fields: int = 0       # needed pairs the run actually obtained
    coverage: float | None = None      # matched / needed -- did it do the job?
    excess_ratio: float | None = None  # distinct / needed -- how far past the purpose?
    elapsed_ms: float = 0.0       # hardware-dependent; reported, not relied on

    @classmethod
    def build(
        cls,
        *,
        fetches: int,
        records: int,
        fields_pulled: int,
        pulled: set[FieldRef],
        needed: set[FieldRef],
        elapsed_ms: float,
        page_loads: int | None = None,
    ) -> "ExtractionCost":
        matched = len(pulled & needed)
        return cls(
            fetches=fetches,
            page_loads=page_loads,
            records=records,
            fields_pulled=fields_pulled,
            distinct_fields=len(pulled),
            needed_fields=len(needed),
            matched_fields=matched,
            coverage=_ratio(matched, len(needed)),
            excess_ratio=_ratio(len(pulled), len(needed)),
            elapsed_ms=round(elapsed_ms, 3),
        )


def combine(costs: list[ExtractionCost]) -> ExtractionCost:
    """Aggregate per-task costs into one profile for a technique.

    Ratios are micro-averaged -- summed numerators over summed denominators --
    rather than averaged per task, so a task with many needed fields weighs more
    than a task with few. That matches how the workload is actually run.
    """

    if not costs:
        return ExtractionCost()

    needed = sum(c.needed_fields for c in costs)
    matched = sum(c.matched_fields for c in costs)
    distinct = sum(c.distinct_fields for c in costs)
    loads = [c.page_loads for c in costs if c.page_loads is not None]
    return ExtractionCost(
        fetches=sum(c.fetches for c in costs),
        page_loads=sum(loads) if loads else None,
        records=sum(c.records for c in costs),
        fields_pulled=sum(c.fields_pulled for c in costs),
        distinct_fields=distinct,
        needed_fields=needed,
        matched_fields=matched,
        coverage=_ratio(matched, needed),
        excess_ratio=_ratio(distinct, needed),
        elapsed_ms=round(sum(c.elapsed_ms for c in costs), 3),
    )


class MeteredSource(HISDataSource):
    """Wraps any ``HISDataSource`` and counts what a technique actually pulled.

    Metering at the adapter boundary means every technique is measured the same
    way without any technique knowing it is being measured -- no cooperation, no
    instrumentation in technique code, and nothing a technique could game. The
    same wrapper will meter a Tier 2 portal adapter unchanged, where ``fetches``
    becomes page loads rather than in-memory queries.
    """

    def __init__(self, inner: HISDataSource) -> None:
        self._inner = inner
        # A portal adapter exposes how many pages its browser has loaded; the
        # meter reports the delta. An in-memory source has no such thing.
        self._loads_at_start: int | None = getattr(inner, "page_loads", None)
        self.fetches = 0
        self.records = 0
        self.fields_pulled = 0
        self.pulled: set[FieldRef] = set()

    def layers(self) -> tuple[HISLayer, ...]:
        return self._inner.layers()

    def fetch(self, layer: HISLayer, **query: Any) -> Iterator[dict[str, Any]]:
        # Counted on call rather than on first iteration, so a technique that
        # requests a layer and consumes nothing is still charged for the request.
        self.fetches += 1
        return self._metered(layer, query)

    def _metered(self, layer: HISLayer, query: dict[str, Any]) -> Iterator[dict[str, Any]]:
        for row in self._inner.fetch(layer, **query):
            self.records += 1
            self.fields_pulled += len(row)
            self.pulled.update((layer.value, name) for name in row)
            yield row

    def close(self) -> None:
        self._inner.close()

    def cost(self, needed: set[FieldRef], elapsed_ms: float) -> ExtractionCost:
        """Freeze what was metered into an ``ExtractionCost``."""

        loads = None
        if self._loads_at_start is not None:
            loads = getattr(self._inner, "page_loads", self._loads_at_start) - self._loads_at_start
        return ExtractionCost.build(
            fetches=self.fetches,
            records=self.records,
            fields_pulled=self.fields_pulled,
            pulled=self.pulled,
            needed=needed,
            elapsed_ms=elapsed_ms,
            page_loads=loads,
        )
