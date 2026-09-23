"""Build the interactive dataset page: an export, through the pipeline, one screen at a time.

    python tools/build_dataset_page.py data/public_synthea --column-map data/public_synthea/column_map.json
    python tools/build_dataset_page.py data/hospital_export --column-map data/hospital_export/column_map.json

Runs the dataset path for real -- the handling gate, the adapter, the
benchmark on the pipeline's four tasks, and one patient's single-patient tasks
through ours, the AI agent (told the policy) and the baseline, each scored by
the harness exactly as the benchmark scores it -- and writes a self-contained
page (``tools/dataset_page.html`` + one JSON block, no network, no libraries):

    1  Files in      each file, each header: recognised (and its DPDP category),
                     dropped by the map, or never understood
    2  The gate      the four handling checks; switch one off to see the refusal
    3  One patient   what each technique read, took and exported, for one patient
    4  The score     the benchmark on this export, and the coverage ceiling
    5  Retention     the export's erasure date; drag past it to watch the purge

The page obeys the rules it demonstrates:

* **No raw direct identifier is ever on it.** Patients are shown by their
  pseudonym; a raw identifier the baseline exported is shown masked, in red.
  The builder searches its own output for every direct identifier and contact
  value the export holds, and refuses to write the page if one is there.
* **A real export's values are not shown at all.** Unless the export is
  synthetic (a synthetic manifest, or ``Synthetic: yes`` in its provenance
  note), clinical, financial and quasi-identifying values are replaced by their
  shape: the page shows structure, counts and pseudonyms only.
* **A real export's page is never committable.** Its default path is
  git-ignored, and the builder refuses a path git would track.

# DPDP Act 2023 -- security safeguards, purpose limitation: a demonstration of
# the pipeline is itself processing, and is held to the same rules.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from compliance.audit import AuditLog                                     # noqa: E402
from compliance.benchmark import (                                         # noqa: E402
    _run_task, bind_subject, first_subject, necessary_records, run_benchmark,
)
from compliance.checkers import run_all                                    # noqa: E402
from compliance.handling import check_handling, declares_synthetic, git_ignores  # noqa: E402
from compliance.models import FieldCategory                                # noqa: E402
from compliance.policy import policy_for                                   # noqa: E402
from compliance.pseudonymise import token_for                              # noqa: E402
from data_synthetic.catalogue import FIELD_CATALOGUE, subject_key          # noqa: E402
from extraction.adapters.dataset_his import (                              # noqa: E402
    READABLE, DatasetHISDataSource, load_column_map, read_columns, read_table,
)
from extraction.base import HISDataSource                                  # noqa: E402
from extraction.techniques import (                                        # noqa: E402
    CompliantExtractionTechnique, UnconstrainedExtractionTechnique, default_techniques,
)
from interop.layers import HISLayer                                        # noqa: E402
from interop.normalise import audit as audit_export, normalise              # noqa: E402
from tools.page_kit import render, write                                   # noqa: E402

TEMPLATE = ROOT / "tools" / "dataset_page.html"
DEFAULT_OUT = ROOT / "docs" / "benchmark_results" / "dataset-walkthrough.html"

LAYER_LABEL = {
    "patient_administration": "Patient administration",
    "clinical_ehr": "Clinical / EHR",
    "ancillary_departmental": "Ancillary / departmental",
    "administrative_financial": "Administrative / financial",
    "infrastructure_integration": "Infrastructure / audit",
}
# Values of these categories are never shown raw, synthetic export or not.
HIDDEN_ALWAYS = {FieldCategory.DIRECT_IDENTIFIER, FieldCategory.CONTACT}
SAMPLE_HL7, SAMPLE_FHIR, PATIENTS = 4, 3, 4


class PageLeak(RuntimeError):
    """The built page would carry a raw identifier (or, for a real export, a value)."""


# --------------------------------------------------------------------------- #
# What each technique read, per file

class ReadRecorder(HISDataSource):
    """Passes every fetch through to the dataset and notes which files the rows came from."""

    def __init__(self, source: DatasetHISDataSource) -> None:
        self.source = source
        self.read: dict[str, int] = {}

    def layers(self):
        return self.source.layers()

    def fields(self, layer):
        return self.source.fields(layer)

    def fetch(self, layer, **query):
        for name, n in self.source.rows_by_file(layer, fields=query.get("fields"), where=query.get("where")).items():
            self.read[name] = self.read.get(name, 0) + n
        return self.source.fetch(layer, **query)


# --------------------------------------------------------------------------- #
# Masking

def mask(value: Any) -> str:
    """'cc3eac4a-34a7-...-8087135631b7' -> 'cc••••••b7': recognisably raw, not readable."""

    s = str(value)
    return "••••" if len(s) <= 4 else f"{s[:2]}{'•' * min(6, len(s) - 4)}{s[-2:]}"


def _category(layer: str, name: str) -> FieldCategory | None:
    return FIELD_CATALOGUE.get(HISLayer(layer), {}).get(name)


def _sensitive_values(rows: dict[str, list[dict]], values_shown: bool) -> dict[str, str]:
    """raw value -> what the page shows instead, for one technique's rows."""

    out: dict[str, str] = {}
    for layer, items in rows.items():
        for row in items:
            for name, value in row.items():
                if value in (None, ""):
                    continue
                cat = _category(layer, name)
                if cat in HIDDEN_ALWAYS:
                    out[str(value)] = mask(value)
                elif not values_shown and len(str(value)) >= 3:
                    out[str(value)] = f"‹{cat.value if cat else 'value'}›"
    return out


def _apply(text: str, replacements: dict[str, str]) -> str:
    for raw in sorted(replacements, key=len, reverse=True):
        if raw in text:
            text = text.replace(raw, replacements[raw])
    return text


def _hl7_shape(message: str) -> str:
    """A real export's HL7: segment names, field positions and pseudonyms; every value blanked."""

    out = []
    for seg in message.split("\r"):
        parts = seg.split("|")
        if parts[0] == "MSH":
            out.append(seg)
            continue
        out.append("|".join([parts[0]] + [p if (not p or p.startswith("PSN-")) else "▒▒" for p in parts[1:]]))
    return "\r".join(out)


def _fhir_shape(resource: Any) -> Any:
    keep = {"resourceType", "system", "status", "currency"}
    if isinstance(resource, dict):
        return {k: (v if k in keep else _fhir_shape(v)) for k, v in resource.items()}
    if isinstance(resource, list):
        return [_fhir_shape(v) for v in resource]
    if isinstance(resource, str) and resource.startswith("PSN-"):
        return resource
    return "▒▒"


# --------------------------------------------------------------------------- #
# Sections

def files_section(source: DatasetHISDataSource) -> list[dict]:
    out = []
    for path in sorted(p for p in source.directory.iterdir() if p.suffix.lower() in READABLE):
        headers = [str(h) for h in read_table(path, nrows=1).columns]
        reading = read_columns(headers, source.map_for(path.name), min_confidence=source.min_confidence)
        read = path.name in source.file_rows
        layer = reading.layer.value if (read and reading.layer) else None
        columns = []
        for h in headers:
            if h in reading.blanked:
                columns.append({"h": h, "s": "blank"})
                continue
            name = reading.renamed.get(h, h)
            cat = _category(layer, name) if layer else None
            if read and cat is not None:
                columns.append({"h": h, "s": "in", "to": name, "cat": cat.value})
            else:
                columns.append({"h": h, "s": "drop"})
        rows = source.file_rows.get(path.name)
        if rows is None:
            rows = len(read_table(path))
        out.append({"name": path.name, "rows": rows, "layer": layer, "read": read,
                    "confidence": source.file_confidence.get(path.name),
                    "reason": source.unclassified_reason.get(path.name, ""), "columns": columns})
    return out


def layers_section(source: DatasetHISDataSource) -> list[dict]:
    out = []
    for layer in source.layers():
        names = source.merged.get(layer, [source.files[layer].name])
        out.append({"layer": layer.value, "label": LAYER_LABEL[layer.value], "files": names,
                    "stacked": layer in source.stacked, "rows": len(source._frames[layer]),
                    "fields": source.fields(layer)})
    return out


def gate_section(directory: Path) -> dict:
    passed = check_handling(directory)
    # The same checks on a directory that fails every one of them: the exact refusal text.
    scratch = Path(tempfile.mkdtemp(prefix="gate-"))
    try:
        failed = {name: detail for name, _, detail in check_handling(scratch).checks}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return {
        "synthetic_manifest": passed.synthetic,
        "checks": [{"name": n, "ok": ok, "detail": d, "fail": failed.get(n, "")} for n, ok, d in passed.checks],
    }


def _field_view(task, rows: dict[str, list[dict]]) -> list[dict]:
    allowed = {c.value for c in policy_for(task.purpose).allowed_categories}
    needed = task.field_refs()
    out = []
    for layer, items in rows.items():
        names = sorted({k for r in items for k in r})
        for name in names:
            cat = _category(layer, name)
            out.append({"layer": layer, "field": name, "cat": cat.value if cat else None,
                        "needed": (layer, name) in needed, "allowed": bool(cat and cat.value in allowed)})
    return out


def _export_view(output, key: str, values_shown: bool) -> dict:
    shaped = normalise(output, key=key)
    check = audit_export(output, shaped)
    replace = _sensitive_values(output.rows, values_shown)
    hl7, fhir = [], []
    # Registration first: it is where the patient's identity is, so it is where
    # a leak -- or its absence -- shows.
    order = {name: i for i, name in enumerate(LAYER_LABEL)}
    for layer, msgs in sorted(shaped.hl7.items(), key=lambda kv: order.get(kv[0], 99)):
        for m in msgs[:SAMPLE_HL7 if not hl7 else 2]:
            text = m if values_shown else _hl7_shape(m)
            hl7.append({"layer": layer, "text": _apply(text, replace).replace("\r", "\n")})
    for layer, resources in sorted(shaped.fhir.items(), key=lambda kv: order.get(kv[0], 99)):
        for r in resources[:SAMPLE_FHIR if not fhir else 1]:
            body = r if values_shown else _fhir_shape(r)
            fhir.append({"layer": layer, "text": _apply(json.dumps(body, indent=2, ensure_ascii=False), replace)})
    return {"counts": shaped.counts(), "pseudonymised": shaped.pseudonymised,
            "audit": check.one_line(), "leaked": check.leaked, "identifiers": check.identifier_values,
            "hl7": hl7, "fhir": fhir}


def _pick_patients(source: DatasetHISDataSource) -> list[str]:
    """The benchmark's patient first, then the ones with the most varied records."""

    pa = HISLayer.PATIENT_ADMINISTRATION
    if pa not in source.layers():
        return []
    key = subject_key(pa)
    first = first_subject(source)
    ranked = []
    for row in source.fetch(pa, fields=[key]):
        mrn = str(row.get(key, ""))
        if not mrn or mrn == first:
            continue
        spread = 0
        for layer in source.layers():
            if layer is pa or subject_key(layer) is None:
                continue
            spread += len(source.rows_by_file(layer, fields=[subject_key(layer)], where={subject_key(layer): mrn}))
        ranked.append((spread, mrn))
    ranked.sort(key=lambda t: -t[0])
    return ([first] if first else []) + [m for _, m in ranked[: PATIENTS - 1]]


def trace_section(source, tasks, agents, key: str, values_shown: bool) -> tuple[list[dict], dict]:
    pa = HISLayer.PATIENT_ADMINISTRATION
    patients = []
    for mrn in _pick_patients(source):
        label = ""
        if values_shown:
            row = next(iter(source.fetch(pa, fields=["sex", "date_of_birth"], where={"mrn": mrn})), {})
            label = " · ".join(str(v) for v in (row.get("sex"), str(row.get("date_of_birth", ""))[:4]) if v)
        own = {}
        for layer in source.layers():
            k = subject_key(layer)
            if k:
                own.update(source.rows_by_file(layer, fields=[k], where={k: mrn}))
        patients.append({"id": mrn, "token": token_for(mrn, key=key), "label": label, "records": own})

    # Every AI model at the briefing that hands it the purpose policy, each its own key.
    techniques = [("ours", CompliantExtractionTechnique()),
                  *[(f"agent:{agent.short_id}", agent) for agent in agents],
                  ("baseline", UnconstrainedExtractionTechnique())]

    traces: dict[str, dict] = {}
    baseline_cache: dict[str, dict] = {}
    for task in [t for t in tasks if t.single_subject]:
        for p in patients:
            [bound] = bind_subject([task.model_copy(update={"subject": None})], source, subject=p["id"])
            necessary = necessary_records(bound, source)
            for kind, technique in techniques:
                if kind == "baseline" and task.task_id in baseline_cache:
                    # The baseline reads every patient whichever one is asked about:
                    # its pull does not change; only the patient's own count does.
                    view = dict(baseline_cache[task.task_id])
                    view["own"] = necessary
                    view["record_excess"] = round(view["records"] / necessary, 1) if necessary else None
                    traces[f"{task.task_id}|{p['token']}|{kind}"] = view
                    continue
                recorder = ReadRecorder(source)
                [run] = _run_task(technique, bound, recorder, 1, necessary)
                report = run_all(run.output.run, run.output.records)
                view = {
                    "run_id": run.output.run.run_id, "technique": technique.name,
                    "read": recorder.read, "records": run.cost.records, "own": necessary,
                    "record_excess": run.cost.record_excess, "coverage": run.cost.coverage,
                    "score": report.compliance_score,
                    "rules": [{"id": r.rule_id, "title": r.title, "status": r.status.value, "score": r.score,
                               "finding": (r.findings[0] if r.findings else "")} for r in report.results],
                    "fields": _field_view(bound, run.output.rows),
                    "manifest": {"retention_days": run.output.run.retention_days,
                                 "pseudonymised": run.output.run.security.identifiers_pseudonymised,
                                 "deletion": run.output.run.deletion_mechanism or "",
                                 "onward": list(run.output.run.secondary_uses)},
                    "export": _export_view(run.output, key, values_shown),
                }
                if kind == "baseline":
                    baseline_cache[task.task_id] = view
                traces[f"{task.task_id}|{p['token']}|{kind}"] = view
    for p in patients:
        del p["id"]          # the raw record number never reaches the page
    return patients, traces


def benchmark_section(result) -> dict:
    def row(s, flagged=False):
        kind = "ours" if s.short == "compliance-aware" else ("baseline" if s.short == "unconstrained" else "agent")
        return {"name": s.technique, "kind": kind, "briefing": s.briefing, "flagged": flagged,
                "score": s.mean_compliance_score, "coverage": s.cost.coverage, "excess": s.cost.excess_ratio,
                "record_excess": s.cost.record_excess, "records": s.cost.records,
                "fields_pulled": s.cost.fields_pulled, "traps": s.traps_note(),
                "rules": s.per_rule_mean, "per_task": s.per_task}
    return {
        "by_model": [row(s, f) for s, f in result.by_model()],
        "all": [row(s) for s in result.scores],
        "rule_ids": result.rule_ids,
        "ceiling": {"needed": result.coverage_needed, "in_source": result.coverage_in_source,
                    "reachable": result.coverage_reachable},
        "takeaway": result._takeaway(),
    }


def retention_section(traces: dict[str, dict], tasks, today: date) -> list[dict]:
    out = []
    kinds = list(dict.fromkeys(k.split("|")[-1] for k in traces))
    for task in [t for t in tasks if t.single_subject]:
        for kind in kinds:
            view = next((v for k, v in traces.items() if k.startswith(f"{task.task_id}|") and k.endswith(f"|{kind}")),
                        None)
            if view is None:
                continue
            days = view["manifest"]["retention_days"]
            run_id = view["run_id"]
            out.append({"task": task.task_id, "kind": kind, "technique": view["technique"], "days": days,
                        "ceiling": policy_for(task.purpose).max_retention_days,
                        "erase_after": (today + timedelta(days=days)).isoformat() if days else None,
                        "mechanism": view["manifest"]["deletion"],
                        "files": [f"{run_id}.hl7", f"{run_id}.fhir.json"], "run_id": run_id})
    return out


# --------------------------------------------------------------------------- #

def _identifier_corpus(source: DatasetHISDataSource, values_shown: bool) -> set[str]:
    """Every value the page must not contain: direct identifiers and contact data always;
    for a real export, every clinical and financial value of some length as well."""

    corpus: set[str] = set()
    for layer in source.layers():
        frame = source._frames[layer]
        for name in frame.columns:
            cat = FIELD_CATALOGUE[layer].get(name)
            strict = cat in HIDDEN_ALWAYS
            if not strict and (values_shown or cat not in (FieldCategory.CLINICAL, FieldCategory.FINANCIAL)):
                continue
            floor = 4 if strict else 8
            corpus |= {str(v) for v in frame[name].dropna().unique() if len(str(v)) >= floor}
    return corpus


def build(directory: Path, *, column_map: dict | None = None, file_maps: dict | None = None,
          out: Path = DEFAULT_OUT, enforce_handling: bool = True, audit_log: AuditLog | None = None,
          today: date | None = None) -> dict:
    from run_pipeline import TASKS

    directory = Path(directory)
    today = today or date.today()
    values_shown = declares_synthetic(directory)
    if not values_shown and not git_ignores(out):
        raise PageLeak(f"{out} is not git-ignored: a page built from a real export must never be committable")

    source = DatasetHISDataSource(directory, column_map=column_map, file_maps=file_maps,
                                  enforce_handling=enforce_handling)
    if not source.layers():
        raise SystemExit("the adapter understood none of the files -- fill the column map first (check_source.py)")
    key = token_for(directory.resolve(), key="dataset-page")        # stable pseudonyms per export
    techniques = default_techniques(TASKS, source)
    agents = [t for t in techniques if getattr(t, "briefing", None) == "policy"]
    result = run_benchmark(techniques, TASKS, source, dataset_note=f"dataset {directory.name}",
                           audit=audit_log or AuditLog())
    patients, traces = trace_section(source, TASKS, agents, key, values_shown)
    files = files_section(source)
    data = {
        "meta": {"dataset": directory.name, "generated": today.isoformat(), "values_shown": values_shown,
                 "agents": [{"key": f"agent:{a.short_id}", "name": a.model} for a in agents]},
        "files": files,
        "layers": layers_section(source),
        "gate": gate_section(directory),
        "tasks": [{"id": t.task_id, "purpose": t.purpose.value, "description": t.description,
                   "single": t.single_subject, "trap": t.trap or "",
                   "needs": [{"layer": lf.layer.value, "field": f} for lf in t.needed for f in lf.fields]}
                  for t in TASKS],
        "patients": patients,
        "traces": traces,
        "benchmark": benchmark_section(result),
        "retention": retention_section(traces, TASKS, today),
        "layer_labels": LAYER_LABEL,
        "funnel": {
            "files": len(files), "files_read": sum(f["read"] for f in files),
            "columns": sum(len(f["columns"]) for f in files),
            "columns_in": sum(c["s"] == "in" for f in files for c in f["columns"]),
            "columns_blank": sum(c["s"] == "blank" for f in files for c in f["columns"]),
            "columns_drop": sum(c["s"] == "drop" for f in files for c in f["columns"]),
            "rows": sum(f["rows"] for f in files),
            "rows_read": sum(source.file_rows.values()),
        },
    }
    page = render(TEMPLATE, data, current="dataset", out=out)

    # The page's own audit: nothing it must not show is on it.
    found = [v for v in _identifier_corpus(source, values_shown) if v in page]
    if found:
        raise PageLeak(f"{len(found)} value(s) that must not be shown would be on the page -- not written")
    write(out, page)
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path, help="the export directory (under data/)")
    parser.add_argument("--column-map", help="JSON: export header -> catalogue field")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    column_map, file_maps = load_column_map(args.column_map)
    data = build(args.dataset, column_map=column_map, file_maps=file_maps, out=args.out)
    f = data["funnel"]
    print(f"  wrote {args.out}")
    print(f"  {f['files_read']} of {f['files']} files read; {f['columns_in']} of {f['columns']} columns entered; "
          f"{len(data['patients'])} patients traced; values {'shown (synthetic)' if data['meta']['values_shown'] else 'hidden (real export)'}")
    print("  page audit: no raw identifier on the page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
