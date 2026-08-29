"""Synthetic-data-backed implementation of ``HISDataSource``.

Thin slice of build step 4: wraps ``data_synthetic`` so downstream code
(compliance scoring now, the agent later) pulls records through the same
interface a live HIS source will implement. "Extraction" here is field selection
over a generated dataset -- a stand-in for Tier 2 scraping, not the scraping
itself.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from data_synthetic.generators.records import build_dataset
from extraction.base import HISDataSource
from interop.layers import HISLayer


class MockHISDataSource(HISDataSource):
    """Serves synthetic records through the ``HISDataSource`` API."""

    def __init__(self, records_per_layer: int = 5, *, seed: int | None = None) -> None:
        self._data: dict[HISLayer, list[dict[str, Any]]] = build_dataset(
            records_per_layer, seed=seed
        )

    def layers(self) -> tuple[HISLayer, ...]:
        return tuple(self._data)

    def fetch(
        self,
        layer: HISLayer,
        *,
        fields: list[str] | None = None,
        **query: Any,
    ) -> Iterator[dict[str, Any]]:
        """Yield records for ``layer``; if ``fields`` is given, project to those."""

        for row in self._data.get(layer, []):
            if fields is None:
                yield dict(row)
            else:
                yield {name: row[name] for name in fields if name in row}
