"""Erase exports whose declared retention has run out -- the deletion mechanism.

    python scripts/purge_exports.py                    # what is scheduled, and what is due today
    python scripts/purge_exports.py --erase            # erase what is due, and log it
    python scripts/purge_exports.py --as-of 2026-12-01 --erase   # as it would run on that day

Every export the pipeline writes carries a retention sidecar
(``<run_id>.retention.json``): the purpose, the retention the manifest
declared, and the date after which the files must go. This script is the purge
the capability register calls PURGE-01. Each erasure is written to the audit
log, so storage limitation is something the pipeline does and can show, not
something a manifest says.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from compliance.audit import AuditLog
from compliance.benchmark import ARTIFACT_DIR
from compliance.retention import purge_expired, schedules


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=str(ARTIFACT_DIR), help="where the exports were written")
    parser.add_argument("--as-of", help="YYYY-MM-DD: evaluate the schedule as of this date (default: now)")
    parser.add_argument("--erase", action="store_true", help="actually erase what is due (default: report only)")
    args = parser.parse_args()

    directory = Path(args.directory)
    now = (datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc) if args.as_of
           else datetime.now(timezone.utc))
    audit = AuditLog()

    print(present.banner("Retention: what is scheduled, what is due, what goes"))
    print(f"  directory : {directory}")
    print(f"  as of     : {now:%Y-%m-%d}")
    print()
    listed = schedules(directory)
    if not listed:
        print("  no scheduled exports here (run scripts/run_pipeline.py first)")
        return
    for sched in listed:
        due = sched.due(now)
        print(f"  {'DUE ' if due else '    '} {sched.one_line()}")
    print()

    due_paths = purge_expired(directory, now=now, audit=audit, dry_run=True)
    if not due_paths:
        print("  nothing is due; nothing erased")
        return
    if not args.erase:
        print(f"  {len(due_paths)} file(s) due for erasure -- re-run with --erase to erase them:")
        for p in due_paths:
            print(f"    {p.name}")
        return
    erased = purge_expired(directory, now=now, audit=audit)
    print(f"  erased {len(erased)} file(s):")
    for p in erased:
        print(f"    {p.name}")
    print()
    print("  audit log:")
    print(audit.render_tail(3))


if __name__ == "__main__":
    main()
