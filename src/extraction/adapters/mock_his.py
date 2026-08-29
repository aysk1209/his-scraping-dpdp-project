"""Synthetic-data-backed implementation of `HISDataSource`.

Wraps the `data_synthetic` generators behind the extraction interface. This is
the source every downstream module is developed against until live HIS access
is usable.

Placeholder for build step 1; implemented in build step 4.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from extraction.base import HISDataSource
from interop.layers import HISLayer


class MockHISDataSource(HISDataSource):
    """Serves records produced by `data_synthetic` through the `HISDataSource` API."""

    def layers(self) -> tuple[HISLayer, ...]:
        raise NotImplementedError("Implemented in build step 4 against synthetic data.")

    def fetch(self, layer: HISLayer, **query: Any) -> Iterator[dict[str, Any]]:
        raise NotImplementedError("Implemented in build step 4 against synthetic data.")
