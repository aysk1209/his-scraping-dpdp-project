"""A breach drill: an export leaks, and the hospital must tell the Board and the patients.

    python scripts/breach_drill.py
    python scripts/breach_drill.py --run RUN_ID [--run ...] --what "how it leaked" [--log PATH] [--exports DIR]

The drill takes one job -- the patient summary, about one patient -- and exports
it two ways: as ours does (only that patient's records, identifiers replaced by
tokens) and as the coverage-optimised baseline would (every patient's records,
identifiers raw; written here only so there is something to leak -- the
pipeline itself never keeps the baseline's export). Then the export folder is
"copied to an unencrypted drive", and each export is assessed from the audit
log alone: whose data, which categories, in what form, and how serious.

The notices a breach requires are drafted from the assessment -- to the Data
Protection Board and to each affected patient -- without a single value from a
record. Finding the patients to notify needs the audit key and the register,
which the data-protection contact holds (``compliance.breach.resolve``).

Last, the same leak found 31 days later: the export had passed its erasure
date. A file that should already have been purged is a finding of its own.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present                                                   # noqa: E402
from compliance.audit import AuditLog, fields_by_layer                       # noqa: E402
from compliance.breach import assess, resolve                                 # noqa: E402

LEAK = "the folder of exports was copied to an unencrypted USB drive that was then lost"


def _indent(text: str) -> str:
    return "\n".join("  " + line for line in text.split("\n"))


def demo() -> int:
    from compliance.benchmark import bind_subject
    from extraction.adapters.mock_his import MockHISDataSource
    from extraction.metering import MeteredSource
    from extraction.techniques.compliant import CompliantExtractionTechnique
    from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique
    from interop.layers import HISLayer
    from interop.normalise import normalise
    from run_benchmark import TASKS

    print(present.banner("Breach drill: an export leaks"))
    source = MockHISDataSource(records_per_layer=20, seed=42)
    [task] = bind_subject([next(t for t in TASKS if t.task_id == "patient-summary")], source)
    register = [r["mrn"] for r in source.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"])]

    with tempfile.TemporaryDirectory() as tmp:
        log = AuditLog(Path(tmp) / "audit.jsonl")
        exports = Path(tmp) / "exports"
        runs = {}
        for label, technique in (("ours", CompliantExtractionTechnique()),
                                 ("baseline", UnconstrainedExtractionTechnique())):
            metered = MeteredSource(source)
            out = technique.extract(metered, task)
            log.extraction(out.run, technique=technique.name, records=len(out.records),
                           fields=fields_by_layer({(lv, f) for lv, rows in out.rows.items() for r in rows for f in r}),
                           source="drill, 20 patients", rows=out.rows, scoped_to=metered.subject_scope())
            normalise(out).to_files(exports, audit=log)
            runs[label] = out.run.run_id

        results = {label: assess([run_id], description=LEAK, log=log, export_dirs=[exports])
                   for label, run_id in runs.items()}

        print(present.rule())
        print(f"1. The same job, two exports, one leak: {LEAK}")
        print()
        print(f"  {'':<10} {'patients':>8}  {'identifiers':<14} {'categories':<54} severity")
        for label, a in results.items():
            print(f"  {label:<10} {len(a.affected):>8}  {'raw' if a.raw_identifiers() else 'pseudonymised':<14} "
                  f"{', '.join(a.categories()):<54} {a.severity()}")
        print()
        print("  The job was about one patient. Ours exported that patient, as tokens; the baseline")
        print("  exported every patient, as themselves. Minimisation is also the size of a breach.")

        print(present.rule())
        print("2. The intimation to the Data Protection Board (ours)")
        print()
        print(_indent(results["ours"].to_board()))
        print()
        print("3. The notice each affected patient receives (ours) -- the same for each, naming no one")
        print()
        print(_indent(results["ours"].to_patient()))
        print()
        found = resolve(results["ours"], register)
        print(f"  The data-protection contact resolves the tokens against the register with the audit key:")
        print(f"  {len(found)} patient(s) to notify for ours; "
              f"{len(resolve(results['baseline'], register))} had it been the baseline's export.")

        print(present.rule())
        print("4. The same leak, found 31 days later")
        late = assess([runs["ours"]], description=LEAK, log=log, export_dirs=[exports],
                      now=results["ours"].discovered_at + timedelta(days=31))
        overdue = [e for e in late.exports if e.overdue]
        print(f"  {len(overdue)} export(s) had passed the erasure date their manifest declared. The purge should")
        print("  have removed them; that they were there to be copied is a finding the Board is told of:")
        print()
        print(_indent("\n".join(line for line in late.to_board().split("\n") if "Retention" in line)))
    print(present.rule())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--run", action="append", default=[], help="run id of an exposed export; repeatable")
    parser.add_argument("--what", default=LEAK, help="what happened, in a sentence")
    parser.add_argument("--log", type=Path, help="audit log (default: data/audit/extraction-audit.jsonl)")
    parser.add_argument("--exports", type=Path, action="append", default=[], help="export directory; repeatable")
    args = parser.parse_args()
    if not args.run:
        return demo()
    a = assess(args.run, description=args.what, log=AuditLog(args.log) if args.log else None,
               export_dirs=args.exports)
    print(a.to_board())
    print()
    print(a.to_patient())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
