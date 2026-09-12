"""File-backed ``HISDataSource``: a hospital export read through the same interface.

The expected export is a directory of tabular files -- CSV or Excel -- one per
HIS layer or one per module, plus optionally a ``manifest.json``. Nothing here
depends on the files being ours: every file is classified by its *content*.

    Which layer is this file?   ``infer_layer`` over its column names -- the same
                                classification the Tier 2 crawler applies to a
                                portal module, so a spreadsheet and a web page are
                                understood the same way.
    What are the columns called? Whatever the hospital called them. A
                                ``column_map`` renames export headers to catalogue
                                fields (``{"Patient ID": "mrn"}``); unmapped columns
                                that already match the catalogue are kept as-is;
                                anything else is dropped and reported, never
                                silently carried through.

This is the piece that turns the real dataset -- when it arrives -- into a
configuration step: point it at the directory, supply the column map, and the
techniques, rules, benchmark and export run unchanged. Until then it is exercised
against ``data_synthetic.export.write_export``, which writes files of the right
shape.

Handling note: a real export is real personal data. PLAN.md section 4 governs
where it may live (``data/``, git-ignored) and what must be confirmed first.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from data_synthetic.catalogue import FIELD_CATALOGUE, infer_layer
from extraction.base import HISDataSource
from interop.layers import HISLayer

_READERS = {".csv": pd.read_csv, ".xlsx": pd.read_excel, ".xls": pd.read_excel}


class DatasetHISDataSource(HISDataSource):
    """Serves a directory of exported tables through the ``HISDataSource`` API."""

    def __init__(
        self,
        directory: str | Path,
        *,
        column_map: dict[str, str] | None = None,
        min_confidence: float = 0.5,
    ) -> None:
        self.directory = Path(directory)
        self.column_map = dict(column_map or {})
        self.min_confidence = min_confidence
        self.files: dict[HISLayer, Path] = {}
        self.confidence: dict[HISLayer, float] = {}
        self.dropped_columns: dict[str, list[str]] = {}      # file name -> columns not understood
        self.unclassified: list[str] = []                     # files no layer explains
        self._frames: dict[HISLayer, pd.DataFrame] = {}
        self._load()

    # ---------------------------------------------------------------- loading

    def _load(self) -> None:
        if not self.directory.is_dir():
            raise FileNotFoundError(f"export directory not found: {self.directory}")
        for path in sorted(self.directory.iterdir()):
            reader = _READERS.get(path.suffix.lower())
            if reader is None:
                continue
            frame = reader(path)
            frame = frame.rename(columns=self.column_map)
            layer, confidence = infer_layer(list(frame.columns))
            if layer is None or confidence < self.min_confidence:
                self.unclassified.append(path.name)
                continue
            known = [c for c in frame.columns if c in FIELD_CATALOGUE[layer]]
            dropped = [c for c in frame.columns if c not in FIELD_CATALOGUE[layer]]
            if dropped:
                self.dropped_columns[path.name] = dropped
            # Two files for one layer: keep the better-explained one.
            if layer in self.confidence and self.confidence[layer] >= confidence:
                continue
            self.files[layer] = path
            self.confidence[layer] = confidence
            self._frames[layer] = frame[known].astype(object).where(frame[known].notna(), None)

    # ----------------------------------------------------------------- source

    def layers(self) -> tuple[HISLayer, ...]:
        return tuple(self._frames)

    def fetch(
        self,
        layer: HISLayer,
        *,
        fields: list[str] | None = None,
        **query: Any,
    ) -> Iterator[dict[str, Any]]:
        frame = self._frames.get(layer)
        if frame is None:
            return
        wanted = [f for f in (fields or list(frame.columns)) if f in frame.columns]
        for record in frame[wanted].to_dict(orient="records"):
            yield {k: v for k, v in record.items() if v is not None}

    def describe(self) -> str:
        lines = [f"dataset at {self.directory}"]
        for layer, path in self.files.items():
            lines.append(
                f"  {path.name:<34} -> {layer.value:<26} "
                f"({self.confidence[layer]:.0%} of columns explained, {len(self._frames[layer])} rows)"
            )
        for name, cols in self.dropped_columns.items():
            lines.append(f"  {name}: columns not understood and dropped: {', '.join(cols)}")
        for name in self.unclassified:
            lines.append(f"  {name}: no layer explains its columns -- skipped")
        return "\n".join(lines)
