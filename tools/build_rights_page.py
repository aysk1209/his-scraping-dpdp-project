"""Build the patient-rights page: a patient asks, an export leaks.

    python tools/build_rights_page.py

Runs the benchmark's eight tasks for ours and the baseline over 20 synthetic
patients, with the audit log naming whom each run read (as keyed tokens), and
exports one job both ways. Then, from the log alone:

- for every patient, the runs of each technique that read their records, and
  the access summary the data-protection contact would send
  (``compliance.access_report``);
- for a leaked export of the same job, what each technique's export exposed,
  graded, with the notices to the Board and to the patient
  (``compliance.breach``).

The page carries no value from a record and only masked record numbers; the
builder refuses to write it if any record number appears in the output.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from compliance.access_report import access_summary, mask                     # noqa: E402
from compliance.audit import AuditLog, fields_by_layer, subject_token          # noqa: E402
from compliance.benchmark import bind_subject, run_benchmark                   # noqa: E402
from compliance.breach import assess                                           # noqa: E402
from extraction.adapters.mock_his import MockHISDataSource                     # noqa: E402
from extraction.metering import MeteredSource                                  # noqa: E402
from extraction.techniques.compliant import CompliantExtractionTechnique       # noqa: E402
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique  # noqa: E402
from interop.layers import HISLayer                                            # noqa: E402
from interop.normalise import normalise                                        # noqa: E402
from scripts.run_benchmark import TASKS                                        # noqa: E402
from tools.page_kit import REVIEW_DIR, render, write, part_path   # noqa: E402

TEMPLATE = ROOT / "tools" / "rights_page.html"
DEFAULT_OUT = part_path("rights")
LEAK = "the folder of exports was copied to an unencrypted USB drive that was then lost"


def build(out: Path = DEFAULT_OUT, *, patients: int = 20) -> dict:
    source = MockHISDataSource(records_per_layer=patients, seed=42)
    ours, base = CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()
    tasks = bind_subject(TASKS, source)
    register = [r["mrn"] for r in source.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"])]
    purposes = {t.task_id: t.purpose.value for t in tasks}
    about = next(t.subject for t in tasks if t.single_subject)

    with tempfile.TemporaryDirectory() as tmp:
        log = AuditLog(Path(tmp) / "audit.jsonl")
        exports = Path(tmp) / "exports"
        run_benchmark([ours, base], tasks, source, dataset_note=f"rights page, {patients} patients", audit=log)
        summary_task = next(t for t in tasks if t.task_id == "patient-summary")
        normalise(ours.extract(source, summary_task)).to_files(exports, audit=log)

        events = [e for e in log.entries() if e.event == "extraction"]
        people = []
        for mrn in register:
            token = subject_token(mrn)
            read = {"ours": [], "baseline": []}
            for e in events:
                if token in e.subjects:
                    key = "ours" if e.technique == ours.name else "baseline"
                    read[key].append(e.run_id.split("--")[0])
            summary = access_summary(mrn, log=log, export_dirs=[exports])
            # The same activities as data, for the page to set out; field names and categories only.
            activities = [{"at": a.at.strftime("%Y-%m-%d %H:%M"), "task": a.run_id.split("--")[0],
                           "kind": "ours" if a.technique == ours.name else "baseline", "purpose": a.purpose,
                           "categories": {c: len(fs) for c, fs in a.categories.items()},
                           "exported": a.exported, "pseudonymised": a.pseudonymised,
                           "erase_after": a.erase_after.strftime("%Y-%m-%d") if a.erase_after else None}
                          for a in summary.activities]
            people.append({"id": mask(mrn), "about": mrn == about, "ours": sorted(set(read["ours"])),
                           "baseline": sorted(set(read["baseline"])), "activities": activities,
                           "summary": summary.render().replace(str(log.path), "the audit log")})

        # The breach: the same job exported both ways, the folder lost.
        leak_log = AuditLog(Path(tmp) / "leak.jsonl")
        leak_dir = Path(tmp) / "leak"
        runs = {}
        for label, technique in (("ours", ours), ("baseline", base)):
            meter = MeteredSource(source)
            output = technique.extract(meter, summary_task)
            leak_log.extraction(output.run, technique=technique.name, records=len(output.records),
                                fields=fields_by_layer({(lv, f) for lv, rows in output.rows.items()
                                                        for r in rows for f in r}),
                                rows=output.rows, scoped_to=meter.subject_scope())
            normalise(output).to_files(leak_dir, audit=leak_log)
            runs[label] = output.run.run_id
        breach = {}
        for label, run_id in runs.items():
            a = assess([run_id], description=LEAK, log=leak_log, export_dirs=[leak_dir])
            breach[label] = {"patients": len(a.affected), "raw": a.raw_identifiers(), "categories": a.categories(),
                             "severity": a.severity(), "board": a.to_board(), "patient": a.to_patient()}
        late = assess([runs["ours"]], description=LEAK, log=leak_log, export_dirs=[leak_dir],
                      now=assess([runs["ours"]], description=LEAK, log=leak_log).discovered_at + timedelta(days=31))
        breach["late"] = {"overdue": sum(1 for e in late.exports if e.overdue),
                          "line": next((l.split(":", 1)[1].strip() for l in late.to_board().split("\n")
                                        if "Retention" in l), "")}

    bystanders = [p for p in people if not p["about"]]
    data = {
        "people": people, "purposes": purposes, "tasks": [t.task_id for t in tasks],
        "breach": breach,
        "meta": {"patients": patients,
                 "ours_bystander": max(len(p["ours"]) for p in bystanders),
                 "base_bystander": max(len(p["baseline"]) for p in bystanders),
                 "tasks": len(tasks)},
    }
    html = render(TEMPLATE, data, current="rights", out=out)
    leaked = [m for m in register if m in html]
    if leaked:
        raise SystemExit(f"refusing to write {out}: {len(leaked)} record number(s) would appear on the page")
    write(out, html)
    return data


def main() -> int:
    data = build()
    m, b = data["meta"], data["breach"]
    print(f"  wrote {DEFAULT_OUT}")
    print(f"  a bystander read in {m['ours_bystander']} of {m['tasks']} runs (ours) vs {m['base_bystander']} "
          f"(baseline); a leak exposes {b['ours']['patients']} vs {b['baseline']['patients']} patients")
    return 0


if __name__ == "__main__":
    sys.exit(main())
