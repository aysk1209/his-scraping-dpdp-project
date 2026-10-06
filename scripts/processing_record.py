"""Write the record of processing activities from the audit log.

    python scripts/processing_record.py                 # from data/audit/extraction-audit.jsonl
    python scripts/processing_record.py --log PATH --out FILE

The record is derived, not maintained: per purpose, the lawful basis on
record, what was read and by whom, how many patients (counted, never named),
what was exported and what erased. Run it after any pipeline or benchmark run;
it cannot fall behind what ran. Written under data/ (git-ignored) by default.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compliance.audit import AuditLog                       # noqa: E402
from compliance.processing_record import build_record       # noqa: E402

DEFAULT_OUT = ROOT / "data" / "audit" / "processing-record.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--log", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    record = build_record(AuditLog(args.log) if args.log else AuditLog())
    text = record.render_markdown()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
