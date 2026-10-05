"""The journey of one entry: a row of an export, followed through the whole pipeline.

    python scripts/trace_journey.py                                  # Synthea, the first patient
    python scripts/trace_journey.py --row 5 --task claim-reconciliation
    python scripts/trace_journey.py data/hospital_export --column-map data/hospital_export/column_map.json

The benchmark is the aggregate; this is the opposite view. One line of the
export's registration file (and that patient's first diagnosis line) is taken
through the seven stages ``run_pipeline.py`` runs, with the real code at every
stage:

    1 DATASET     the entry as the file holds it; the handling gate
    2 UNDERSTAND  each column: read as a catalogue field (and its DPDP
                  category), dropped by the column map, or never understood;
                  the value as the adapter holds it; the patient across the export
    3 EXTRACT     one task about this patient, through ours, each AI agent told
                  the policy, and the baseline; what each took; the seven rules
    4 NORMALISE   the HL7 v2 / FHIR export; the identifier's pseudonym; the
                  export audit
    5 PURPOSE     the same pull, judged under every purpose
    6 ASSIST      which staff role may be walked through each field it holds
    7 RETAIN      the audit log the harness wrote, the retention sidecar, and
                  the purge on the day it falls due

For every column of the entry the journey also records its *fate* at each
stage -- "SSN: dropped by the column map, never read", "BIRTHDATE: read as
date_of_birth, taken, exported, erased after 30 days" -- which is what
``tools/build_journey_page.py`` lets a room click through.

Values: an export that declares itself synthetic (Synthea does) has its values
shown, except direct identifiers and contact details, which are masked
everywhere, and every column the pipeline never reads, which is masked too --
it stops at the door, so its content is not the point. A real export shows
shape only. The raw record number never leaves this function; the pseudonym
does.

# DPDP Act 2023 -- purpose limitation, data minimisation, storage limitation,
# security safeguards: each stage below is where one of them is enforced.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import _present as present                                                  # noqa: E402
from compliance.audit import AuditLog, fields_by_layer                      # noqa: E402
from compliance.benchmark import _run_task, bind_subject, necessary_records  # noqa: E402
from compliance.checkers import run_all                                     # noqa: E402
from compliance.handling import declares_synthetic                          # noqa: E402
from compliance.models import FieldCategory                                 # noqa: E402
from compliance.policy import PURPOSE_POLICY, policy_for                    # noqa: E402
from compliance.pseudonymise import token_for                               # noqa: E402
from compliance.purpose_matrix import score_across_purposes                 # noqa: E402
from compliance.retention import purge_expired, schedules                   # noqa: E402
from compliance.roles import StaffRole, role_policy                         # noqa: E402
from data_synthetic.catalogue import FIELD_CATALOGUE, subject_key           # noqa: E402
from extraction.adapters.dataset_his import (                               # noqa: E402
    DatasetHISDataSource, load_column_map, read_columns, read_table,
)
from extraction.techniques import (                                         # noqa: E402
    CompliantExtractionTechnique, UnconstrainedExtractionTechnique, default_techniques,
)
from interop.layers import HISLayer                                         # noqa: E402
from interop.normalise import audit as audit_export, normalise               # noqa: E402
from tools.build_dataset_page import (                                      # noqa: E402
    ReadRecorder, _export_view, _identifier_corpus, gate_section,
)

DEFAULT_DATASET = ROOT / "data" / "public_synthea"
STAGES = [
    ("dataset", "Dataset"), ("understand", "Understand"), ("extract", "Extract"),
    ("normalise", "Normalise"), ("purpose", "Purpose"), ("assist", "Assist"), ("retain", "Retain"),
]
HIDDEN_ALWAYS = {FieldCategory.DIRECT_IDENTIFIER, FieldCategory.CONTACT}
PA, CLIN = HISLayer.PATIENT_ADMINISTRATION, HISLayer.CLINICAL_EHR
LABEL = {"patient_administration": "Patient administration", "clinical_ehr": "Clinical / EHR",
         "ancillary_departmental": "Ancillary / departmental",
         "administrative_financial": "Administrative / financial",
         "infrastructure_integration": "Infrastructure / audit"}


# --------------------------------------------------------------------------- #
# What may be shown

def mask(value: Any) -> str:
    """A value recognisably there but not readable: 'cc3eac4a-...-31b7' -> 'cc••••••b7'."""

    s = str(value)
    return "••••" if len(s) <= 6 else f"{s[:2]}{'•' * min(6, len(s) - 4)}{s[-2:]}"


def _category(layer: HISLayer | None, name: str | None) -> FieldCategory | None:
    return FIELD_CATALOGUE.get(layer, {}).get(name) if layer and name else None


def shown(value: Any, cat: FieldCategory | None, *, read: bool, values_shown: bool) -> str:
    if value is None or str(value) in ("", "nan", "NaT", "None"):
        return ""
    if not values_shown:
        return f"‹{cat.value}›" if cat else "▒▒"
    if not read or cat in HIDDEN_ALWAYS:
        return mask(value)
    return str(value)


# --------------------------------------------------------------------------- #
# The entries: the registration row, and the same patient's first diagnosis row

def _reading(source: DatasetHISDataSource, path: Path):
    headers = [str(h) for h in read_table(path, nrows=1).columns]
    return headers, read_columns(headers, source.map_for(path.name), min_confidence=source.min_confidence)


def _adapter_row(source: DatasetHISDataSource, layer: HISLayer, file_name: str, mrn: str) -> dict:
    """The row as the adapter holds it: from that file, for that patient, normalised."""

    frame = source._frames[layer]
    key = subject_key(layer)
    mask_rows = frame[key].astype(str) == mrn
    if layer in source._row_file:
        mask_rows &= source._row_file[layer] == file_name
    hit = frame[mask_rows]
    return {} if hit.empty else hit.iloc[0].dropna().to_dict()


def _entry(source, layer: HISLayer, path: Path, raw: dict, line: int, rows: int, mrn: str, values_shown: bool) -> dict:
    headers, reading = _reading(source, path)
    adapted = _adapter_row(source, layer, path.name, mrn)
    columns = []
    for h in headers:
        if h in reading.blanked:
            status, field = "blank", None
        else:
            field = reading.renamed.get(h, h)
            status = "in" if _category(layer, field) is not None else "drop"
            field = field if status == "in" else None
        cat = _category(layer, field)
        columns.append({
            "id": f"{path.name}:{h}", "h": h, "status": status, "field": field,
            "cat": cat.value if cat else None,
            "raw": shown(raw.get(h), cat, read=status == "in", values_shown=values_shown),
            "held": shown(adapted.get(field), cat, read=True, values_shown=values_shown) if field else "",
        })
    return {"file": path.name, "layer": layer.value, "line": line, "rows": rows,
            "confidence": source.file_confidence.get(path.name), "columns": columns}


def _find_patient_row(source, layer: HISLayer, field: str, mrn: str):
    """The first line of a file of ``layer`` that carries ``field`` and belongs to this patient."""

    for name in source.merged.get(layer, [source.files[layer].name] if layer in source.files else []):
        path = source.directory / name
        headers, reading = _reading(source, path)
        named = {reading.renamed.get(h, h): h for h in headers if h not in reading.blanked}
        if field not in named or subject_key(layer) not in named:
            continue
        table = read_table(path)
        hits = table.index[table[named[subject_key(layer)]].astype(str) == mrn]
        if len(hits):
            i = int(hits[0])
            return path, table.iloc[i].to_dict(), i + 2, len(table)
    return None


# --------------------------------------------------------------------------- #

def _techniques(source, tasks):
    agents = [t for t in default_techniques(tasks, source) if getattr(t, "briefing", None) == "policy"]
    return [("ours", "Ours", CompliantExtractionTechnique()),
            *[(f"agent:{a.short_id}", a.model, a) for a in agents],
            ("baseline", "Baseline", UnconstrainedExtractionTechnique())]


def _fates(entries, task, runs, token_of_mrn) -> dict[str, list[dict]]:
    """Per technique, per column: what happened to it at each of the seven stages."""

    policy = policy_for(task.purpose)
    needed = task.field_refs()
    out: dict[str, list[dict]] = {}
    for kind, run in runs.items():
        for entry in entries:
            layer = HISLayer(entry["layer"])
            took = run["took"].get(entry["layer"], set())
            for c in entry["columns"]:
                f = [{"s": "ok", "t": f"{entry['file']}, line {entry['line']}"}]
                if c["status"] != "in":
                    f.append({"s": "stop", "t": "dropped by the column map; never read" if c["status"] == "blank"
                              else "not a catalogue field; dropped and reported"})
                    f += [{"s": "none", "t": ""}] * 5
                    out[f"{kind}|{c['id']}"] = f
                    continue
                cat = FieldCategory(c["cat"])
                f.append({"s": "ok", "t": f"read as {c['field']} ({c['cat'].replace('_', ' ')})"})
                allowed = cat in policy.allowed_categories
                need = (layer.value, c["field"]) in needed
                if c["field"] not in took:
                    f.append({"s": "warn" if need else "ok",
                              "t": "needed, not taken" if need else "left behind: not needed for the job"})
                    f += [{"s": "none", "t": ""}] * 4
                    out[f"{kind}|{c['id']}"] = f
                    continue
                if not allowed:
                    f.append({"s": "bad", "t": f"taken: {c['cat'].replace('_', ' ')} is out of scope for "
                                               f"{task.purpose.value.replace('_', ' ')}"})
                else:
                    f.append({"s": "ok" if need else "warn", "t": "taken: needed for the job" if need else "taken: not needed"})
                if cat is FieldCategory.DIRECT_IDENTIFIER:
                    f.append({"s": "ok", "t": f"exported as {token_of_mrn}" if c["field"] == subject_key(layer)
                              else "exported as a pseudonym"} if run["pseudonymised"]
                             else {"s": "bad", "t": "exported raw: the identifier left"})
                else:
                    f.append({"s": "warn" if cat is FieldCategory.CONTACT else "ok", "t": "exported as written"})
                lawful = [p.value.replace("_", " ") for p, pol in PURPOSE_POLICY.items() if cat in pol.allowed_categories]
                f.append({"s": "ok" if allowed else "bad",
                          "t": ("lawful under " + ", ".join(lawful)) if lawful else "lawful under no modelled purpose"})
                roles = [r.value for r in StaffRole if cat in role_policy(r).allowed_categories()]
                f.append({"s": "ok" if roles else "bad", "t": ("seen by " + ", ".join(roles)) if roles else "no role may see it"})
                f.append({"s": "ok", "t": f"erased on {run['erase']} ({run['days']} d)"} if run["erase"]
                         else {"s": "bad", "t": "no retention declared: kept indefinitely"})
                out[f"{kind}|{c['id']}"] = f
    return out


def journey(directory: Path = DEFAULT_DATASET, *, column_map: dict | None = None, file_maps: dict | None = None,
            row: int = 0, enforce_handling: bool = True, today: date | None = None) -> dict:
    """Run one entry through every stage; everything the page and the terminal show."""

    from run_pipeline import TASKS

    directory = Path(directory)
    today = today or date.today()
    values_shown = declares_synthetic(directory)
    source = DatasetHISDataSource(directory, column_map=column_map, file_maps=file_maps, enforce_handling=enforce_handling)
    if PA not in source.layers():
        raise SystemExit("no file was read as patient administration -- fill the column map first (check_source.py)")
    key = token_for(directory.resolve(), key="dataset-page")     # the same pseudonyms as the dataset page

    # 1 -- the entry, and the patient it belongs to
    reg = source.files[PA]
    table = read_table(reg)
    if not 0 <= row < len(table):
        raise SystemExit(f"{reg.name} has {len(table)} rows; --row {row} is outside it")
    raw = table.iloc[row].to_dict()
    headers, reading = _reading(source, reg)
    mrn_header = next(h for h in headers if h not in reading.blanked and reading.renamed.get(h, h) == subject_key(PA))
    mrn = str(raw[mrn_header])
    token = token_for(mrn, key=key)
    entries = [_entry(source, PA, reg, raw, row + 2, len(table), mrn, values_shown)]
    if CLIN in source.layers():
        found = _find_patient_row(source, CLIN, "primary_diagnosis", mrn)
        if found:
            path, crow, line, n = found
            entries.append(_entry(source, CLIN, path, crow, line, n, mrn, values_shown))

    footprint, samples = [], []
    for layer in source.layers():
        k = subject_key(layer)
        if not k:
            continue
        for name, n in source.rows_by_file(layer, fields=[k], where={k: mrn}).items():
            footprint.append({"layer": layer.value, "file": name, "rows": n})
        first = next(iter(source.fetch(layer, where={k: mrn})), None)
        if first:
            samples.append({"layer": layer.value, "fields": [
                {"field": f, "cat": (_category(layer, f).value if _category(layer, f) else None),
                 "value": shown(v, _category(layer, f), read=True, values_shown=values_shown)}
                for f, v in first.items()]})

    # 3..7 -- the single-patient tasks, through every technique, for real
    techniques = _techniques(source, TASKS)
    scratch = Path(tempfile.mkdtemp(prefix="journey-"))
    audit = AuditLog(scratch / "extraction-audit.jsonl")
    tasks_out, fates = [], {}
    try:
        for task in [t for t in TASKS if t.single_subject]:
            [bound] = bind_subject([task.model_copy(update={"subject": None})], source, subject=mrn)
            necessary = necessary_records(bound, source)
            runs: dict[str, dict] = {}
            for kind, label, technique in techniques:
                recorder = ReadRecorder(source)
                [run] = _run_task(technique, bound, recorder, 1, necessary)
                output = run.output
                audit.extraction(output.run, technique=technique.name, records=len(output.records),
                                 fields=fields_by_layer(set(run.key[0])), source=f"dataset {directory.name}",
                                 rows=output.rows)
                report = run_all(output.run, output.records)
                shaped = normalise(output, key=key)
                check = audit_export(output, shaped)
                where = scratch / "exports" / f"{task.task_id}--{kind.replace(':', '-')}"
                written = shaped.to_files(where, audit=audit)
                sizes = {p.name: p.stat().st_size for p in written if p.exists()}
                sched = next(iter(schedules(where)), None)
                erase, erased = None, []
                if sched and sched.delete_after:
                    erase = sched.delete_after.date().isoformat()
                    erased = [p.name for p in purge_expired(where, now=sched.delete_after, audit=audit)]
                matrix = score_across_purposes(output.run, output.records)
                took = {layer: set(names) for layer, names in fields_by_layer(set(run.key[0])).items()}
                runs[kind] = {"took": took, "pseudonymised": output.run.security.identifiers_pseudonymised,
                              "erase": erase, "days": output.run.retention_days}
                runs[kind]["view"] = {
                    "kind": kind, "label": label, "technique": technique.name, "run_id": output.run.run_id,
                    "score": report.compliance_score, "records": run.cost.records, "own": necessary,
                    "record_excess": run.cost.record_excess, "coverage": run.cost.coverage,
                    "read": recorder.read,
                    "fields": [{"layer": layer, "field": f, "cat": (_category(HISLayer(layer), f).value
                                                                    if _category(HISLayer(layer), f) else None),
                                "needed": (layer, f) in bound.field_refs(),
                                "allowed": bool(_category(HISLayer(layer), f)
                                                in policy_for(task.purpose).allowed_categories)}
                               for layer, names in sorted(took.items()) for f in sorted(names)],
                    "rules": [{"id": r.rule_id, "title": r.title, "status": r.status.value,
                               "finding": r.findings[0] if r.findings else ""} for r in report.results],
                    "manifest": {"retention_days": output.run.retention_days,
                                 "pseudonymised": output.run.security.identifiers_pseudonymised,
                                 "onward": list(output.run.secondary_uses),
                                 "deletion": output.run.deletion_mechanism or ""},
                    "export": _export_view(output, key, values_shown, shaped=shaped),
                    "purposes": [{"purpose": v.purpose, "declared": v.is_declared_purpose, "score": v.compliance_score,
                                  "verdict": v.verdict(), "out_of_scope": v.out_of_scope_categories}
                                 for v in matrix.verdicts],
                    "retain": {"files": sizes, "erase_after": erase, "days": output.run.retention_days,
                               "ceiling": policy_for(task.purpose).max_retention_days, "erased": erased,
                               "mechanism": output.run.deletion_mechanism or ""},
                    "log": [{"event": e.event, "at": (erase if e.event == "purge" else today.isoformat()),
                             "records": e.records, "note": e.note,
                             "fields": {k: v for k, v in e.fields.items()}}
                            for e in audit.for_run(output.run.run_id)],
                }
            fates.update({f"{task.task_id}|{k}": v for k, v in _fates(entries, task, runs, token).items()})
            tasks_out.append({"id": task.task_id, "purpose": task.purpose.value, "description": task.description,
                              "trap": task.trap or "", "own": necessary,
                              "needs": [{"layer": lf.layer.value, "field": f} for lf in task.needed for f in lf.fields],
                              "allowed": sorted(c.value for c in policy_for(task.purpose).allowed_categories),
                              "ceiling": policy_for(task.purpose).max_retention_days,
                              "runs": [r["view"] for r in runs.values()]})
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    data = {
        "meta": {"dataset": directory.name, "generated": today.isoformat(), "values_shown": values_shown,
                 "token": token, "mrn_shown": shown(mrn, FieldCategory.DIRECT_IDENTIFIER, read=True, values_shown=values_shown),
                 "techniques": [{"kind": k, "label": label} for k, label, _ in techniques]},
        "stages": [{"id": s, "label": l} for s, l in STAGES],
        "gate": gate_section(directory),
        "entries": entries,
        "footprint": footprint,
        "samples": samples,
        "layer_labels": LABEL,
        "tasks": tasks_out,
        "roles": [{"id": r.value, "description": role_policy(r).description,
                   "allowed": sorted(c.value for c in role_policy(r).allowed_categories())} for r in StaffRole],
        "purposes": {p.value: {"allowed": sorted(c.value for c in pol.allowed_categories),
                               "ceiling": pol.max_retention_days} for p, pol in PURPOSE_POLICY.items()},
        "fates": fates,
    }
    # Nothing that must not be shown is in what this returns (the raw record number included).
    corpus = _identifier_corpus(source, values_shown) | {mrn}
    blob = json.dumps(data, ensure_ascii=False)
    leaked = [v for v in corpus if len(v) >= 4 and v in blob]
    if leaked:
        raise RuntimeError(f"{len(leaked)} value(s) that must not be shown would leave the journey")
    return data


# --------------------------------------------------------------------------- #
# The terminal view

def _task(data: dict, task_id: str) -> dict:
    for t in data["tasks"]:
        if t["id"] == task_id:
            return t
    raise SystemExit(f"no single-patient task {task_id!r}; choose from: {', '.join(t['id'] for t in data['tasks'])}")


def print_journey(data: dict, task_id: str) -> None:
    m, task = data["meta"], _task(data, task_id)
    reg = data["entries"][0]
    print(present.banner(f"THE JOURNEY OF ONE ENTRY -- {reg['file']}, line {reg['line']}  ({m['dataset']})"))
    print(f"  patient {m['mrn_shown']}  ->  {m['token']} from the moment it is exported")
    print(f"  values {'shown (synthetic export); identifiers and unread columns masked' if m['values_shown'] else 'hidden: a real export shows shape only'}")

    print(present.banner("1 DATASET -- the entry as the file holds it; the handling gate"))
    for c in reg["columns"]:
        print(f"  {c['h']:<22} {c['raw']}")
    for ch in data["gate"]["checks"]:
        print(f"  [{'x' if ch['ok'] else ' '}] {ch['name']}: {ch['detail']}")

    print(present.banner("2 UNDERSTAND -- column by column; the patient across the export"))
    for e in data["entries"]:
        print(f"  {e['file']} -> {LABEL[e['layer']]}")
        for c in e["columns"]:
            fate = (f"-> {c['field']:<20} {c['cat']:<18} held as {c['held']}" if c["status"] == "in"
                    else "dropped by the column map" if c["status"] == "blank" else "not understood; dropped")
            print(f"    {c['h']:<22} {fate}")
    for fp in data["footprint"]:
        print(f"  {fp['file']:<26} {fp['rows']:>6} row(s) of this patient")

    print(present.banner(f"3 EXTRACT -- {task['id']} ({task['purpose']}): {task['description']}"))
    if task["trap"]:
        print(f"  trap: {task['trap']}")
    for r in task["runs"]:
        oos = [f["field"] for f in r["fields"] if not f["allowed"]]
        print(f"  {r['label']:<24} score {r['score']:.3f}   {r['records']:>7} records read "
              f"({task['own']} are this patient's)   {len(r['fields'])} fields"
              + (f"   OUT OF SCOPE: {', '.join(oos)}" if oos else ""))

    print(present.banner("4 NORMALISE -- the export and its audit"))
    for r in task["runs"]:
        print(f"  {r['label']:<24} {r['export']['audit']}")

    print(present.banner("5 PURPOSE -- the same pull, under every purpose"))
    for r in task["runs"]:
        print(f"  {r['label']:<24} " + "   ".join(f"{v['purpose']}{'*' if v['declared'] else ''} {v['score']:.2f}"
                                               for v in r["purposes"]))

    print(present.banner("6 ASSIST -- who may be walked through each field ours took"))
    ours = task["runs"][0]
    for f in ours["fields"]:
        roles = [r["id"] for r in data["roles"] if f["cat"] in r["allowed"]]
        print(f"  {f['field']:<22} {f['cat']:<18} {', '.join(roles) or 'no role'}")

    print(present.banner("7 RETAIN -- the log the harness wrote, and the purge"))
    for r in task["runs"]:
        rt = r["retain"]
        print(f"  {r['label']:<24} " + (f"kept {rt['days']} d; erased {rt['erase_after']}: {', '.join(rt['erased'])}"
                                         if rt["erase_after"] else "no retention declared: never erased"))
        for e in r["log"]:
            print(f"      {e['at']}  {e['event']:<10} {e['note'] or str(e['records']) + ' records'}")

    print(present.banner("FOLLOW -- each column of the entry, through the seven stages (ours)"))
    for e in data["entries"]:
        for c in e["columns"]:
            fate = data["fates"][f"{task['id']}|ours|{c['id']}"]
            last = next((s for s in reversed(fate) if s["s"] != "none"), fate[0])
            print(f"  {e['file'] + ':' + c['h']:<34} {last['t']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dataset", nargs="?", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--column-map", help="JSON: export header -> catalogue field (default: the export's column_map.json)")
    parser.add_argument("--row", type=int, default=0, help="which row of the registration file (0 = the first patient)")
    parser.add_argument("--task", default="patient-summary")
    args = parser.parse_args()
    if not args.dataset.exists():
        raise SystemExit(f"{args.dataset} is not here -- python scripts/fetch_public_dataset.py puts Synthea's sample there")
    cmap = args.column_map or (args.dataset / "column_map.json" if (args.dataset / "column_map.json").exists() else None)
    column_map, file_maps = load_column_map(cmap)
    print_journey(journey(args.dataset, column_map=column_map, file_maps=file_maps, row=args.row), args.task)
    return 0


if __name__ == "__main__":
    sys.exit(main())
