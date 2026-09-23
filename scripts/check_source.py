"""Day-one diagnostic: what does the system understand about a new data source?

    python scripts/check_source.py data/hospital_export
    python scripts/check_source.py data/hospital_export --column-map data/column_map.json
    python scripts/check_source.py data/hospital_export --write-map data/column_map.json
    python scripts/check_source.py https://portal.example/ --user U --password P [--aliases FILE] [--write-map FILE]

Points at a directory of exported files or a portal URL and reports what the
pipeline made of it -- which files or modules it found, which HIS layer it
inferred for each and how confidently, which columns or headers it recognised,
and which it could not. It extracts nothing: a directory is read for its headers
and row counts; a portal is logged into and crawled the way discovery already
does (one list page and one record per module).

``--write-map`` writes a mapping template with every unrecognised header on the
left and a blank on the right, plus the catalogue's field names for reference,
so the first hour with real data is spent filling in a file, not reading code.

For a directory, the handling checks (PLAN.md section 4) run first. A real
export that is not under data/, not git-ignored, or has no provenance note is
reported and NOT read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from compliance.handling import check_handling
from data_synthetic.catalogue import FIELD_CATALOGUE, SUBJECT_KEY
from extraction.adapters.dataset_his import READABLE, load_column_map, normalise_dates, read_columns, read_table
from interop.layers import HISLayer


def _load_map(path: str | None) -> dict[str, str]:
    """Portal field aliases (blanks are "not yet mapped"). Column maps use ``load_column_map``."""

    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: v for k, v in data.get("map", data).items() if v}


def _write_template(path: Path, unmatched: list[str], existing: dict[str, str], kind: str,
                    file_maps: dict[str, dict[str, str]] | None = None) -> None:
    template = {
        "_about": (
            f"{kind} mapping: left = the header as the source shows it, right = the catalogue field "
            f"it means. Leave a value blank to drop that column. Fields per layer are listed under _catalogue. "
            f"A header that means different fields in different files (a patient id that is 'mrn' on a "
            f"clinical file and 'subject_mrn' on the audit trail) goes under 'files', per file name, "
            f"which overrides 'map' for that file."
        ),
        "map": {**{h: "" for h in unmatched}, **existing},
        "files": file_maps or {},
        "_catalogue": {layer.value: list(fields) for layer, fields in FIELD_CATALOGUE.items()},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(template, indent=2), encoding="utf-8")


def _report_fields(label: str, seen: list[str], layer: HISLayer | None, confidence: float) -> list[str]:
    known = FIELD_CATALOGUE.get(layer, {}) if layer else {}
    recognised = [f for f in seen if f in known]
    unmatched = [f for f in seen if f not in known]
    missing = [f for f in known if f not in seen]
    lines = [f"  {label}"]
    lines.append(f"    inferred layer : {layer.value if layer else '?'} ({confidence:.0%} of headers explained)")
    lines.append(f"    recognised     : {', '.join(recognised) or '-'}")
    lines.append(f"    not understood : {', '.join(unmatched) or '-'}" + ("   <- map these" if unmatched else ""))
    lines.append(f"    catalogue fields absent here: {', '.join(missing) or '-'}")
    return lines


# --------------------------------------------------------------------------- #

def check_directory(directory: Path, column_map: dict[str, str], write_map: Path | None,
                    file_maps: dict[str, dict[str, str]] | None = None) -> int:
    file_maps = file_maps or {}
    print(present.banner(f"Source check -- directory {directory}"))
    report = check_handling(directory)
    print(report.render())
    if not report.ok:
        print("\n  Not reading anything until the checks pass.")
        return 2

    all_unmatched: list[str] = []
    print()
    files = sorted(p for p in directory.iterdir() if p.suffix.lower() in READABLE)
    if not files:
        print("  no CSV / Excel files found")
        return 1
    suggestions: dict[str, dict[str, str]] = {}
    readable = 0
    for path in files:
        frame = read_table(path, nrows=200)
        headers = [str(c) for c in frame.columns]
        this_map = {**column_map, **file_maps.get(path.name, {})}
        # The adapter's own classifier: what this prints is what the pipeline will do.
        reading = read_columns(headers, this_map)
        layer = reading.layer
        mapped = list(reading.renamed.values())
        for line in _report_fields(f"{path.name}  ({len(frame)}+ rows sampled, {len(headers)} columns)",
                                   mapped, layer, reading.confidence):
            print(line)
        if reading.blanked:
            print(f"    dropped by map : {', '.join(reading.blanked)}")
        if reading.accepted:
            readable += 1
            print(f"    adapter        : reads it as {layer.value}")
        else:
            print(f"    adapter        : NOT READ -- {reading.reason}")
        if layer is not None:
            # A patient-id header mapped to the wrong layer's key: say exactly what to write.
            key = SUBJECT_KEY.get(layer)
            for h, m in reading.renamed.items():
                if m in SUBJECT_KEY.values() and m not in FIELD_CATALOGUE[layer] and key:
                    suggestions.setdefault(path.name, {})[h] = key
                    print(f"    per-file fix    : '{h}' is '{key}' on this layer -> files.\"{path.name}\".\"{h}\" = \"{key}\"")
            sample = frame[list(reading.renamed)].rename(columns=reading.renamed)
            known = [c for c in dict.fromkeys(sample.columns) if c in FIELD_CATALOGUE[layer]]
            _, unparsed = normalise_dates(sample[known])
            dated = [c for c in known if c in ("date_of_birth", "admission_datetime", "encounter_datetime", "event_timestamp")]
            if dated:
                print(f"    dates           : {', '.join(dated)} parsed day-first and emitted in ISO form"
                      + (f"; could not parse: {', '.join(f'{c} x{n}' for c, n in unparsed.items())}" if unparsed else ""))
        known = FIELD_CATALOGUE.get(layer, {}) if layer else {}
        all_unmatched += [h for h, m in reading.renamed.items() if m not in known]
        print()

    print(f"  the adapter will read {readable} of {len(files)} file(s)"
          + ("" if readable else " -- the pipeline will refuse to run on this until the map is filled"))
    print()

    if write_map:
        merged = {**{f: dict(m) for f, m in file_maps.items()}}
        for f, m in suggestions.items():
            merged.setdefault(f, {}).update(m)
        _write_template(write_map, sorted(set(all_unmatched)), column_map, "column", merged)
        print(present.wrote(write_map))
    print("  Next: fill the map, re-run this check, then "
          "python scripts/run_pipeline.py --dataset <dir> --column-map <file>")
    return 0


def check_portal(url: str, user: str, password: str, aliases: dict[str, str], write_map: Path | None) -> int:
    print(present.banner(f"Source check -- portal {url}"))
    from extraction.tier2 import LoginFailed, PortalBrowser, discover
    all_unmatched: list[str] = []
    with PortalBrowser(url, user, password, field_aliases=aliases) as browser:
        try:
            browser.login()
        except LoginFailed as exc:
            print(f"  login failed: {exc}")
            return 2
        print(f"  logged in as {user}")
        nav = discover(browser)
    print(f"  {len(nav.modules)} module(s) found in {nav.page_loads} page loads\n")
    for m in nav.modules:
        seen = m.all_fields()
        for line in _report_fields(f"{m.title}  ({m.list_path}; {m.page_count or '?'} pages, "
                                   f"{m.record_count or '?'} records)", seen, m.inferred_layer, m.layer_confidence):
            print(line)
        known = FIELD_CATALOGUE.get(m.inferred_layer, {}) if m.inferred_layer else {}
        all_unmatched += [f for f in seen if f not in known]
        print()
    if write_map:
        _write_template(write_map, sorted(set(all_unmatched)), aliases, "field-alias")
        print(present.wrote(write_map))
    print("  Next: fill the aliases, re-run this check, then "
          "python scripts/run_pipeline.py --portal <url> --user U --password P --aliases <file>")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="a directory of CSV/Excel files, or a portal URL")
    parser.add_argument("--column-map", help="JSON: export header -> catalogue field")
    parser.add_argument("--aliases", help="JSON: portal header -> catalogue field")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--write-map", type=Path, help="write a mapping template for the unrecognised headers")
    args = parser.parse_args()

    if args.source.startswith(("http://", "https://")):
        if not (args.user and args.password):
            parser.error("--user and --password are required for a portal")
        return check_portal(args.source, args.user, args.password, _load_map(args.aliases), args.write_map)
    column_map, file_maps = load_column_map(args.column_map)
    return check_directory(Path(args.source), column_map, args.write_map, file_maps=file_maps)


if __name__ == "__main__":
    raise SystemExit(main())
