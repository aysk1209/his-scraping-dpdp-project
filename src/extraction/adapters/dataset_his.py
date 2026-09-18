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
                                silently carried through. A header that means
                                different things in different files ("Patient ID"
                                is ``mrn`` on a clinical file and ``subject_mrn``
                                on the audit trail) is mapped per file
                                (``file_maps={"audit_trail.csv": {...}}``).
    One layer, several files?   Concatenated, when their recognised columns
                                agree -- a hospital exports by month, not by
                                layer. Files that disagree are reported and the
                                better-explained one is kept.
    What do the dates look like? However the hospital wrote them. The
                                catalogue's date and datetime fields are parsed
                                (day first, as India writes them) and re-emitted
                                in ISO form, which is what the HL7 v2 and FHIR
                                shapers expect. An unparseable value is left
                                as it was and counted.

This is the piece that turns the real dataset -- when it arrives -- into a
configuration step: point it at the directory, supply the column map, and the
techniques, rules, benchmark and export run unchanged. Until then it is exercised
against ``data_synthetic.export.write_export``, which writes files of the right
shape.

Handling note: a real export is real personal data. PLAN.md section 4 governs
where it may live (``data/``, git-ignored) and what must be confirmed first --
and ``compliance.handling`` enforces it: unless the directory is a synthetic
export, the adapter refuses to read it until the checks pass. ``enforce_handling``
exists for tests that build throwaway files; do not turn it off for real data.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from compliance.handling import require_safe_to_read

from data_synthetic.catalogue import FIELD_CATALOGUE, infer_layer
from extraction.base import HISDataSource
from interop.layers import HISLayer

_READERS = {".csv": pd.read_csv, ".xlsx": pd.read_excel, ".xls": pd.read_excel}

# Catalogue fields that carry a date or a timestamp, and the ISO form each is
# emitted in. The shapers (HL7 PID-7, FHIR birthDate, ...) rely on ISO input.
DATE_FIELDS = {"date_of_birth": "%Y-%m-%d"}
DATETIME_FIELDS = {"admission_datetime": "%Y-%m-%dT%H:%M:%S", "encounter_datetime": "%Y-%m-%dT%H:%M:%S",
                   "event_timestamp": "%Y-%m-%dT%H:%M:%S"}


def normalise_dates(frame: pd.DataFrame, *, dayfirst: bool = True) -> tuple[pd.DataFrame, dict[str, int]]:
    """Re-emit the catalogue's date/datetime columns in ISO form.

    Returns the frame and, per column, how many values could not be parsed
    (those are left untouched, so nothing is invented). Values already in ISO
    form pass through unchanged.
    """

    frame = frame.copy()
    unparsed: dict[str, int] = {}
    for column, fmt in {**DATE_FIELDS, **DATETIME_FIELDS}.items():
        if column not in frame.columns:
            continue
        raw = frame[column]
        # ISO first (unambiguous), then the hospital's day-first form.
        parsed = pd.to_datetime(raw, errors="coerce", format="ISO8601")
        fallback = pd.to_datetime(raw.where(parsed.isna()), errors="coerce", dayfirst=dayfirst)
        parsed = parsed.fillna(fallback)
        bad = int((parsed.isna() & raw.notna()).sum())
        if bad:
            unparsed[column] = bad
        iso = parsed.dt.strftime(fmt)
        frame[column] = iso.where(parsed.notna(), raw)
    return frame, unparsed


class DatasetHISDataSource(HISDataSource):
    """Serves a directory of exported tables through the ``HISDataSource`` API."""

    def __init__(
        self,
        directory: str | Path,
        *,
        column_map: dict[str, str] | None = None,
        file_maps: dict[str, dict[str, str]] | None = None,
        min_confidence: float = 0.5,
        enforce_handling: bool = True,
        dayfirst: bool = True,
    ) -> None:
        self.directory = Path(directory)
        if enforce_handling:
            # Refuses real data that is not under data/, not ignored, or has no
            # provenance note. Synthetic exports pass by their manifest.
            require_safe_to_read(self.directory)
        self.column_map = dict(column_map or {})
        self.file_maps = {k: dict(v) for k, v in (file_maps or {}).items()}
        self.min_confidence = min_confidence
        self.dayfirst = dayfirst
        self.files: dict[HISLayer, Path] = {}                 # the first file of each layer
        self.merged: dict[HISLayer, list[str]] = {}          # layer -> every file concatenated into it
        self.skipped: dict[str, str] = {}                     # file name -> why it was not used
        self.confidence: dict[HISLayer, float] = {}
        self.dropped_columns: dict[str, list[str]] = {}      # file name -> columns not understood
        self.unparsed_dates: dict[str, dict[str, int]] = {}   # file name -> column -> values left as they were
        self.unclassified: list[str] = []                     # files no layer explains
        self._frames: dict[HISLayer, pd.DataFrame] = {}
        self._load()

    def map_for(self, file_name: str) -> dict[str, str]:
        """The column map for one file: the global map, overridden per file."""

        return {**self.column_map, **self.file_maps.get(file_name, {})}

    # ---------------------------------------------------------------- loading

    def _load(self) -> None:
        if not self.directory.is_dir():
            raise FileNotFoundError(f"export directory not found: {self.directory}")
        for path in sorted(self.directory.iterdir()):
            reader = _READERS.get(path.suffix.lower())
            if reader is None:
                continue
            frame = reader(path)
            frame = frame.rename(columns=self.map_for(path.name))
            layer, confidence = infer_layer(list(frame.columns))
            if layer is None or confidence < self.min_confidence:
                self.unclassified.append(path.name)
                continue
            known = [c for c in frame.columns if c in FIELD_CATALOGUE[layer]]
            dropped = [c for c in frame.columns if c not in FIELD_CATALOGUE[layer]]
            if dropped:
                self.dropped_columns[path.name] = dropped
            frame, unparsed = normalise_dates(frame[known], dayfirst=self.dayfirst)
            if unparsed:
                self.unparsed_dates[path.name] = unparsed
            frame = frame.astype(object).where(frame.notna(), None)
            if layer in self._frames:
                # A second file for the same layer: a hospital exports by
                # month or by ward. Same recognised columns -> one table.
                if set(known) == set(self._frames[layer].columns):
                    self._frames[layer] = pd.concat([self._frames[layer], frame[list(self._frames[layer].columns)]],
                                                    ignore_index=True)
                    self.merged.setdefault(layer, [self.files[layer].name]).append(path.name)
                    continue
                # Different columns: keep the better-explained file, and say so.
                if self.confidence[layer] >= confidence:
                    self.skipped[path.name] = (f"also {layer.value}, but its columns differ from "
                                               f"{self.files[layer].name}; not merged")
                    continue
                self.skipped[self.files[layer].name] = (f"also {layer.value}, but its columns differ from "
                                                        f"{path.name}; not merged")
            self.files[layer] = path
            self.confidence[layer] = confidence
            self._frames[layer] = frame

    # ----------------------------------------------------------------- source

    def layers(self) -> tuple[HISLayer, ...]:
        return tuple(self._frames)

    def fetch(
        self,
        layer: HISLayer,
        *,
        fields: list[str] | None = None,
        where: dict[str, Any] | None = None,
        **query: Any,
    ) -> Iterator[dict[str, Any]]:
        frame = self._frames.get(layer)
        if frame is None:
            return
        for k, v in (where or {}).items():
            frame = frame[frame[k].astype(str) == str(v)] if k in frame.columns else frame.iloc[0:0]
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
        for layer, names in self.merged.items():
            lines.append(f"  {layer.value}: {len(names)} files concatenated ({', '.join(names)})")
        for name, cols in self.dropped_columns.items():
            lines.append(f"  {name}: columns not understood and dropped: {', '.join(cols)}")
        for name, cols in self.unparsed_dates.items():
            lines.append(f"  {name}: dates left as written (could not parse): "
                         + ", ".join(f"{c} x{n}" for c, n in cols.items()))
        for name, why in self.skipped.items():
            lines.append(f"  {name}: {why}")
        for name in self.unclassified:
            lines.append(f"  {name}: no layer explains its columns -- skipped")
        return "\n".join(lines)
