"""Scale: what each technique costs as the portal grows.

    python scripts/run_scale.py                       # 20, 40, 80, 160 records per module
    python scripts/run_scale.py --records 20 --records 500

The four-task portal workload, run against the fixture portal at growing sizes,
ours against the coverage-optimised baseline (the AI agents sit between, and
their cost is the fields they ask for, not the portal's size). For each size:
the page loads each technique paid, its wall-clock, its compliance score, and
how many records it read for each one the tasks needed.

What to look for: ours reads one patient through the search box for the tasks
about one patient, so those stay flat; it grows only where a task genuinely
covers every patient (the ward census), and then by the pages that task needs.
The baseline reads everyone for every task, so its cost grows many times faster
with every admission -- and so does what it holds that it should not.

Writes ``docs/benchmark_results/scale.{json,md}``.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present                                                       # noqa: E402
from compliance.audit import AuditLog                                            # noqa: E402
from compliance.benchmark import run_benchmark                                   # noqa: E402
from extraction.adapters.mock_his import MockHISDataSource                       # noqa: E402
from extraction.adapters.portal_his import PortalHISDataSource                   # noqa: E402
from extraction.techniques.compliant import CompliantExtractionTechnique         # noqa: E402
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique  # noqa: E402
from run_pipeline import TASKS as PORTAL_TASKS                                   # noqa: E402
from tools.mock_portal.serve import BackgroundPortal                             # noqa: E402

OUT = ROOT / "docs" / "benchmark_results"
SIZES = [20, 40, 80, 160]


def measure(records: int, page_size: int) -> dict:
    source = MockHISDataSource(records_per_layer=records, seed=42)
    with BackgroundPortal(source, page_size=page_size) as portal, tempfile.TemporaryDirectory() as tmp:
        started = time.perf_counter()
        scraper = PortalHISDataSource(portal.url, portal.username, portal.password)
        discovery = scraper.navigation.page_loads
        result = run_benchmark([CompliantExtractionTechnique(), UnconstrainedExtractionTechnique()],
                               PORTAL_TASKS, scraper, dataset_note=f"scale {records}",
                               audit=AuditLog(Path(tmp) / "a.jsonl"))
        scraper.close()
        total = time.perf_counter() - started
    row = {"records": records, "page_size": page_size, "discovery_loads": discovery, "seconds": round(total, 1)}
    for s in result.scores:
        key = "ours" if s.short == "compliance-aware" else "baseline"
        row[key] = {"score": round(s.mean_compliance_score, 3), "page_loads": s.cost.page_loads,
                    "ms": round(s.cost.elapsed_ms), "record_excess": s.cost.record_excess,
                    "coverage": round(s.cost.coverage, 2)}
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--records", type=int, action="append", help="records per module; repeatable")
    parser.add_argument("--page-size", type=int, default=10)
    args = parser.parse_args()
    sizes = args.records or SIZES

    print(present.banner("Scale: cost as the portal grows"))
    rows = []
    print(f"  {'records':>8} {'ours pages':>11} {'base pages':>11} {'ours s':>8} {'base s':>8} "
          f"{'ours score':>11} {'base score':>11} {'base rec.excess':>16}")
    for n in sizes:
        r = measure(n, args.page_size)
        rows.append(r)
        o, b = r["ours"], r["baseline"]
        print(f"  {n:>8} {o['page_loads']:>11} {b['page_loads']:>11} {o['ms'] / 1000:>8.1f} {b['ms'] / 1000:>8.1f} "
              f"{o['score']:>11.3f} {b['score']:>11.3f} {b['record_excess'] or 0:>16.1f}")

    first, last = rows[0], rows[-1]
    growth = last["records"] / first["records"]
    print()
    print(f"  The portal grew {growth:.0f}x. Ours went from {first['ours']['page_loads']} to "
          f"{last['ours']['page_loads']} page loads; the baseline from {first['baseline']['page_loads']} to "
          f"{last['baseline']['page_loads']}.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scale.json").write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
    md = ["### Scale — cost as the portal grows", "",
          f"The four-task portal workload, {args.page_size} records per page, ours against the baseline. "
          "Wall-clock is hardware-dependent; page loads are not.", "",
          "| Records per module | Ours: page loads | Baseline: page loads | Ours: s | Baseline: s | "
          "Ours: score | Baseline: score | Baseline: records read ÷ needed |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        o, b = r["ours"], r["baseline"]
        md.append(f"| {r['records']} | {o['page_loads']} | {b['page_loads']} | {o['ms'] / 1000:.1f} | "
                  f"{b['ms'] / 1000:.1f} | {o['score']:.3f} | {b['score']:.3f} | {b['record_excess'] or 0:.1f}× |")
    (OUT / "scale.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(present.wrote(OUT / "scale.md"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
