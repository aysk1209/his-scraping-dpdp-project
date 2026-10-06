"""Build the page for the hospital's real export: ``docs/review/real-data.html``.

    python tools/build_real_page.py
    python tools/build_real_page.py --dir data/hospital_export --column-map data/hospital_export/column_map.json

The export handed over on 2026-09-29 is not patient-level: it is a hospital's daily
collection register -- one record per day, receipts by payment mode -- captured to
JSON. So the page shows what the pipeline made of it (the gate, the adapter's
verdict, the benchmark on what the export carries) and a *profile* of the register
itself. Everything shown is a count, a ratio or an index (busiest month = 100): no
rupee amount, no day's figure, no hospital or system name, no scraper session. The
builder searches its own output for each of those before writing, and refuses to
write if one is there.

Run ``scripts/run_pipeline.py --dataset ... --artefact benchmark-real`` first: the
pipeline table is read from that artefact.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd                                                         # noqa: E402

from compliance.handling import check_handling                              # noqa: E402
from compliance.models import Purpose                                       # noqa: E402
from compliance.policy import PURPOSE_POLICY                                # noqa: E402
from compliance.purpose_matrix import score_across_purposes                 # noqa: E402
from data_synthetic.catalogue import FIELD_CATALOGUE                        # noqa: E402
from extraction.technique import ExtractionTask, LayerFields                # noqa: E402
from extraction.techniques.compliant import CompliantExtractionTechnique    # noqa: E402
from interop.layers import HISLayer                                         # noqa: E402
from extraction.adapters.dataset_his import (                               # noqa: E402
    DatasetHISDataSource, is_export_file, load_column_map, read_columns, read_table,
)
from tools.page_kit import REVIEW_DIR, render, write, part_path   # noqa: E402

TEMPLATE = ROOT / "tools" / "real_page.html"
DEFAULT_OUT = part_path("real")
DEFAULT_DIR = ROOT / "data" / "hospital_export"
RESULT = ROOT / "docs" / "benchmark_results" / "benchmark-real.json"

MODES = ("cash", "card", "online", "cheque", "credit")
DIGITAL = ("card", "online")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class Leak(RuntimeError):
    pass


def records_of(directory: Path) -> list[dict]:
    files = [p for p in sorted(directory.iterdir()) if p.suffix.lower() == ".json" and is_export_file(p)]
    if not files:
        raise SystemExit(f"no JSON record file in {directory}")
    return json.loads(files[0].read_text(encoding="utf-8"))


def profile(records: list[dict]) -> dict:
    """Ratios and indices of the register -- never an amount."""

    df = pd.DataFrame(records)
    df["dt"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    money = lambda side, mode: df[f"{side}_{mode}"]                                 # noqa: E731
    take = {s: sum(money(s, m).sum() for m in MODES) for s in ("op", "ip")}
    everything = sum(take.values())

    def mix(side):
        whole = take[side]
        return {m: round(float(money(side, m).sum() / whole), 4) for m in MODES}

    def digital(frame):
        cols = [f"{s}_{m}" for s in ("op", "ip") for m in ("cash", *DIGITAL)]
        whole = frame[cols].sum().sum()
        return float(frame[[f"{s}_{m}" for s in ("op", "ip") for m in DIGITAL]].sum().sum() / whole)

    quarters = df.set_index("dt").resample("QS")
    quarter = [{"label": f"{d.year} Q{(d.month - 1) // 3 + 1}", "digital": round(digital(g.reset_index()), 4),
                "days": int(len(g))} for d, g in quarters if len(g)]
    months = df.set_index("dt").total.resample("MS")
    month_sum, month_days = months.sum(), months.count()
    per_day = month_sum / month_days
    steady = per_day[month_days >= 25]                                              # a part-month is not a month
    base = steady.max()
    month = [{"label": d.strftime("%b %y"), "index": round(float(v / base * 100), 1), "days": int(month_days[d]),
              "part": bool(month_days[d] < 25)} for d, v in per_day.items()]
    by_day = df.groupby(df.dt.dt.dayofweek).total.mean()
    weekday = [{"label": WEEKDAYS[i], "index": round(float(v / df.total.mean() * 100), 1)} for i, v in by_day.items()]

    # The report's own run totals: each weekly capture window repeats its grand total on every row.
    grand = pd.Series([r["totals"]["grand_total"] for r in records])
    windows = df.assign(grand=grand).groupby("date_range")
    reconciled = sum(abs(w.total.sum() - w.grand.iloc[0]) < 1 for _, w in windows)
    parts = df[["op_cash", "op_card", "op_online", "ip_cash", "ip_card", "ip_online"]].sum(axis=1)
    negatives = int(sum((df[c] < 0).sum() for c in df.columns if df[c].dtype == float))
    span = int((df.dt.max() - df.dt.min()).days) + 1
    return {
        "days": int(len(df)), "first": df.dt.min().strftime("%d %b %Y"), "last": df.dt.max().strftime("%d %b %Y"),
        "span_days": span, "distinct_days": int(df.dt.nunique()), "columns": int(len(records[0])),
        "op_share": round(float(take["op"] / everything), 4), "ip_share": round(float(take["ip"] / everything), 4),
        "mix": {"op": mix("op"), "ip": mix("ip")},
        "digital_first": quarter[0]["digital"], "digital_last": quarter[-1]["digital"],
        "quarters": quarter, "months": month, "weekdays": weekday,
        "cancel_share": round(float((df.op_cancel.sum() + df.ip_cancel.sum()) / everything), 4),
        "busiest_weekday": WEEKDAYS[int(by_day.idxmax())], "quietest_weekday": WEEKDAYS[int(by_day.idxmin())],
        "windows": int(windows.ngroups), "windows_reconciled": int(reconciled),
        "total_is_three_modes": int(((parts - df.total).abs() < 1).sum()),
        "negative_cells": negatives, "zero_days": int((df.total == 0).sum()),
        "rows_per_window": {"max": int(windows.size().max()), "min": int(windows.size().min())},
    }


def gate_and_adapter(directory: Path, column_map: dict, file_maps: dict) -> dict:
    handling = check_handling(directory)
    source = DatasetHISDataSource(directory, column_map=column_map, file_maps=file_maps)
    files = []
    for path in sorted(p for p in directory.iterdir() if is_export_file(p)):
        headers = [str(h) for h in read_table(path, nrows=1).columns]
        reading = read_columns(headers, source.map_for(path.name))
        files.append({
            "name": "register.json",                                # the real name says "patient records"; the content is not
            "rows": source.file_rows.get(path.name, 0),
            "layer": reading.layer.value if reading.layer else None,
            "in": [{"h": h, "to": reading.renamed[h]} for h in reading.renamed],
            "blank": len(reading.blanked), "columns": len(headers),
        })
    return {
        "checks": [{"name": n, "ok": ok} for n, ok, _ in handling.checks],
        "files": files, "layers": [l.value for l in source.layers()],
        "fields": {l.value: source.fields(l) for l in source.layers()},
    }


def pipeline(result: dict) -> dict:
    rows = []
    for s in result["scores"]:
        c = s["cost"]
        kind = "ours" if s["short"] == "compliance-aware" else "baseline" if s["short"] == "unconstrained" else "agent"
        rows.append({"kind": kind, "name": s["model"] and f'{s["model"]} ({s["briefing"]})' or s["technique"],
                     "score": s["mean_compliance_score"], "rules": s["rules_passed"], "records": c["records"],
                     "fields": c["distinct_fields"], "excess": c["excess_ratio"], "ms": c["elapsed_ms"],
                     "model": s["model"], "briefing": s["briefing"]})
    return {"rows": rows, "needed": result["coverage_needed"], "carried": result["coverage_in_source"],
            "tasks": [{"id": t["task_id"], "purpose": t["purpose"], "needs": t["needs"]} for t in result["task_details"]],
            "elapsed_ms": result["elapsed_ms"], "audit_events": result["audit_events"],
            "generated": result["generated_at"][:10]}


REGISTER_TASK = ExtractionTask(
    task_id="register-summary",
    purpose=Purpose.BILLING_SETTLEMENT,
    description="Summarise what the hospital took in, for settlement and audit",
    needed=[LayerFields(layer=HISLayer.ADMINISTRATIVE_FINANCIAL, fields=["billed_amount"])],
)

# Questions a hospital asks that need a person in the data. Each is grounded in the
# catalogue: the fields it needs, their categories, and which purposes may take them.
BLOCKED = [
    ("Which patients have an invoice outstanding?", Purpose.BILLING_SETTLEMENT,
     [("administrative_financial", ["mrn", "invoice_id", "billed_amount", "payer_name"])]),
    ("Which diagnoses drive our costs?", Purpose.BILLING_SETTLEMENT,
     [("clinical_ehr", ["primary_diagnosis"]), ("administrative_financial", ["billed_amount"])]),
    ("Who should be reminded of tomorrow's appointment?", Purpose.PATIENT_REGISTRATION,
     [("patient_administration", ["mrn", "full_name", "phone", "admission_datetime"])]),
    ("Who is on which ward right now?", Purpose.CARE_COORDINATION,
     [("patient_administration", ["mrn", "admission_ward"]), ("clinical_ehr", ["encounter_datetime"])]),
]


def purpose_test(source: DatasetHISDataSource) -> dict:
    """The real pull, once, judged under every purpose -- ours reads only what the task needs."""

    output = CompliantExtractionTechnique().extract(source, REGISTER_TASK)
    matrix = score_across_purposes(output.run, output.records)
    return {
        "task": {"id": REGISTER_TASK.task_id, "purpose": REGISTER_TASK.purpose.value, "needs": ["billed_amount"]},
        "records": matrix.record_count, "categories": matrix.extracted_categories,
        "verdicts": [{"purpose": v.purpose, "declared": v.is_declared_purpose, "score": v.compliance_score,
                      "passed": v.rules_passed, "total": v.rules_total, "failed": v.failed_rules,
                      "out_of_scope": v.out_of_scope_categories, "retention": v.retention_limit_days,
                      "verdict": v.verdict()} for v in matrix.verdicts],
    }


def blocked_questions(source: DatasetHISDataSource) -> list[dict]:
    """For each question that needs a person: what it needs, whether this export has it,
    and whether its own purpose would let it be asked at all (the purpose policy's answer)."""

    rows = []
    for question, purpose, needs in BLOCKED:
        pairs = [(HISLayer(layer), f) for layer, fields in needs for f in fields]
        cats = {FIELD_CATALOGUE[layer][f] for layer, f in pairs}
        outside = sorted(c.value for c in cats - PURPOSE_POLICY[purpose].allowed_categories)
        rows.append({"q": question, "purpose": purpose.value, "fields": [f for _, f in pairs],
                     "categories": sorted(c.value for c in cats),
                     "missing": [f for layer, f in pairs if f not in source.fields(layer)],
                     "out_of_scope": outside})
    return rows


def leaks(html: str, records: list[dict]) -> list[str]:
    """What must not be in the page: any daily figure, any address, the scraper session."""

    found = []
    for r in records[:1]:
        for key in ("_source_url", "_session_id"):
            value = str(r[key])
            for part in {value, re.sub(r"^https?://", "", value).split("/")[0]}:
                if part and part in html:
                    found.append(f"{key}: {part[:30]}")
    amounts = sorted({int(r["total"]) for r in records if r["total"] >= 10000})
    plain = set(re.findall(r"(?<![\d.])\d{5,}(?![\d.])", html.replace(",", "")))
    found += [f"amount {a}" for a in amounts if str(a) in plain]
    return found


def build(directory: Path = DEFAULT_DIR, *, column_map: dict | None = None, file_maps: dict | None = None,
          out: Path = DEFAULT_OUT) -> Path:
    if column_map is None:
        column_map, file_maps = load_column_map(directory / "column_map.json")
    records = records_of(directory)
    source = DatasetHISDataSource(directory, column_map=column_map, file_maps=file_maps or {})
    data = {
        "purpose": purpose_test(source),
        "rules": json.loads(RESULT.read_text(encoding="utf-8"))["rule_ids"],
        "blocked": blocked_questions(source),
        "meta": {"built": pd.Timestamp.now().strftime("%Y-%m-%d")},
        "intake": gate_and_adapter(directory, column_map, file_maps or {}),
        "pipeline": pipeline(json.loads(RESULT.read_text(encoding="utf-8"))),
        "register": profile(records),
    }
    html = render(TEMPLATE, data, current="real", out=out)
    found = leaks(html, records)
    if found:
        raise Leak("the page would carry: " + "; ".join(found))
    return write(out, html)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=str(DEFAULT_DIR))
    parser.add_argument("--column-map")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    directory = Path(args.dir)
    column_map, file_maps = load_column_map(args.column_map or directory / "column_map.json")
    out = build(directory, column_map=column_map, file_maps=file_maps, out=Path(args.out))
    print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
