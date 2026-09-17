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
        """Yield records for the given layer as plain dicts.

        Adapters accept ``fields=[...]`` (project to those) and
        ``where={field: value}`` (only records whose field equals the value --
        a portal uses its search box, a file or an in-memory table filters).
        """

    @property
    def transport_secure(self) -> bool | None:
        """Was the connection this source reads over encrypted?

        ``True`` or ``False`` when the source is reached over a network and the
        adapter can see the scheme; ``None`` when there is no transport to
        speak of (an in-memory source, a local file). A technique that declares
        transport encryption is checked against this, not against its own word.
        """

        return None

    def close(self) -> None:
        """Release any resources held by the source. Override if needed."""
