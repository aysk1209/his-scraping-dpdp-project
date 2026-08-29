"""Abstract data-source interface for the extraction layer.

The adapter pattern here is a hard architectural constraint (CLAUDE.md): a
synthetic source (`adapters.mock_his`) and a live HIS source (`adapters.live_his`)
must be interchangeable without any change to downstream compliance or agent
code. Downstream code depends only on `HISDataSource`.

Records cross this boundary as plain dicts. Interoperability shaping
(HL7/FHIR/DICOM/ISO-IEEE-11073) happens in `interop`, not here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from interop.layers import HISLayer


class HISDataSource(ABC):
    """A pluggable source of HIS records, organised by the five-layer architecture."""

    @abstractmethod
    def layers(self) -> tuple[HISLayer, ...]:
        """Return the HIS layers this source can provide records for."""

    @abstractmethod
    def fetch(self, layer: HISLayer, **query: Any) -> Iterator[dict[str, Any]]:
        """Yield records for the given layer as plain dicts."""

    def close(self) -> None:
        """Release any resources held by the source. Override if needed."""
