"""Answer a patient's access request from the audit log -- the data-protection contact's tool.

    python scripts/answer_access_request.py                  # the demonstration (below)
    python scripts/answer_access_request.py --mrn MRN2867825 [--log PATH] [--exports DIR ...]

At the desk the assistant logs the request and routes it here (its task *log a
patient's request for a copy of their data*). This script answers it from
evidence the pipeline wrote -- the audit log, which since 2026-10-06 names the
patients each run read as keyed tokens, and the retention sidecars beside each
export -- never from anyone's recollection.

The demonstration runs the benchmark's eight tasks for ours and the baseline
over 20 synthetic patients, exports one of ours, and then answers two patients:

  1. the patient the single-patient tasks are about -- what was read, for which
     purpose, which categories, what was exported and when it will be erased;
  2. a patient no task was about -- and, side by side, how many runs of each
     technique read their records anyway. Minimisation, seen from the patient.

Nothing printed carries a value from a record, and record numbers are masked.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present                                                   # noqa: E402
from compliance.access_report import access_summary, mask                    # noqa: E402
from compliance.audit import AuditLog, subject_token                         # noqa: E402

DEFAULT_EXPORTS = ROOT / "data" / "exports"


def demo() -> int:
    from compliance.benchmark import bind_subject, first_subject, run_benchmark
    from extraction.adapters.mock_his import MockHISDataSource
    from extraction.techniques.compliant import CompliantExtractionTechnique
    from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique
    from interop.layers import HISLayer
    from interop.normalise import normalise
    from run_benchmark import TASKS

    print(present.banner("A patient asks: what have you done with my data?"))
    source = MockHISDataSource(records_per_layer=20, seed=42)
    ours, baseline = CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()
    with tempfile.TemporaryDirectory() as tmp:
        log = AuditLog(Path(tmp) / "audit.jsonl")
        exports = Path(tmp) / "exports"
        tasks = bind_subject(TASKS, source)
        run_benchmark([ours, baseline], tasks, source, dataset_note="demo, 20 patients", audit=log)
        summary_task = next(t for t in tasks if t.task_id == "patient-summary")
        normalise(ours.extract(source, summary_task)).to_files(exports, audit=log)

        patient = first_subject(source)
        print(present.rule())
        print("1. The patient the single-patient tasks were about")
        print()
        print(access_summary(patient, log=log, export_dirs=[exports]).render())

        rows = list(source.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn"]))
        other = rows[7]["mrn"]
        print()
        print(present.rule())
        print(f"2. A patient no task was about ({mask(other)}): whose runs read their records?")
        token = subject_token(other)
        for technique in (ours.name, baseline.name):
            runs = [e for e in log.entries() if e.event == "extraction" and e.technique == technique]
            touched = [e for e in runs if token in e.subjects]
            tasks_touched = sorted({e.run_id.split("--")[0] for e in touched})
            print(f"  {technique:<26} read them in {len(touched)} of {len(runs)} run(s)"
                  + (f": {', '.join(tasks_touched)}" if tasks_touched else ""))
        print()
        print("  The compliant technique read this patient only where the task covered every patient")
        print("  on a ward or a registry; the baseline read them for every task, including the six that")
        print("  were about somebody else. The log shows it per patient, without holding a record number.")
    print(present.rule())
    return 0


def answer(mrn: str, log_path: Path | None, export_dirs: list[Path]) -> int:
    log = AuditLog(log_path) if log_path else AuditLog()
    print(access_summary(mrn, log=log, export_dirs=export_dirs).render())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mrn", help="the patient's record number; omit for the demonstration")
    parser.add_argument("--log", type=Path, help="audit log (default: data/audit/extraction-audit.jsonl)")
    parser.add_argument("--exports", type=Path, action="append", default=[],
                        help="export directory holding retention sidecars; repeatable")
    args = parser.parse_args()
    if args.mrn:
        return answer(args.mrn, args.log, args.exports or [DEFAULT_EXPORTS])
    return demo()


if __name__ == "__main__":
    raise SystemExit(main())
