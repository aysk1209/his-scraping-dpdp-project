"""Live HIS implementation of `HISDataSource` — Tier 2 credentialed portal scraping.

BLOCKED: build step 7. Credentialed access exists on paper but is not usable
(CLAUDE.md, "Current Phase Constraint"). This module exists so the adapter
boundary is real from day one. It must not be implemented against assumptions
about a real HIS endpoint — wait for actual access.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from extraction.base import HISDataSource
from interop.layers import HISLayer


class LiveHISDataSource(HISDataSource):
    """Credentialed Tier 2 portal scraper. Not usable until live data access is resolved."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Live HIS access is blocked (build step 7). Use MockHISDataSource."
        )

    def layers(self) -> tuple[HISLayer, ...]:
        raise NotImplementedError("Blocked until live HIS data access is resolved.")

    def fetch(self, layer: HISLayer, **query: Any) -> Iterator[dict[str, Any]]:
        raise NotImplementedError("Blocked until live HIS data access is resolved.")
