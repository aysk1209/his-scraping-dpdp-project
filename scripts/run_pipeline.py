"""The whole pipeline, end to end, in one command.

    python scripts/run_pipeline.py                  # 30 records/layer, ~40 s
    python scripts/run_pipeline.py --records 200    # more pages, longer run
    python scripts/run_pipeline.py --show           # watch the browser work

Against real data, once it exists (run scripts/check_source.py first):

    python scripts/run_pipeline.py --dataset data/hospital_export --column-map data/hospital_export/column_map.json
    python scripts/run_pipeline.py --portal https://portal.example/ --user U --password P --aliases FILE

With --dataset, stages 1-2 become "read the export and report what was
understood"; everything downstream is identical. With --portal, the fixture is
not started and the browser is pointed at the given URL instead.

Six stages, each real:

  1. PORTAL     a login-gated HIS portal is served locally over HTTP
  2. DISCOVER   a headless browser logs in, crawls it, and infers what each
                module holds from the field names it finds -- never told
  3. BENCHMARK  the three techniques scrape it, unchanged from the in-memory
                version; every run is scored on the same seven DPDP rules and
                metered for cost, with real page loads
  4. NORMALISE  the compliant run's rows are shaped into HL7 v2 and FHIR with
                direct identifiers pseudonymised on export; the baseline's are
                shaped too, and an audit of both exports shows the difference
  5. PURPOSE    the compliant run is re-judged under every purpose
  6. ASSIST     the staff-guidance assistant answers a question per role, with
                each step placed on the page the crawler found -- and declines
                the one it must

Nothing in here touches a real hospital system. The portal is our fixture; the
scraper does not know that.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from agent import ReplyKind, Session, StaffRole
from compliance.benchmark import run_benchmark
from compliance.models import Purpose
from compliance.purpose_matrix import score_across_purposes
from extraction.adapters.dataset_his import DatasetHISDataSource
from extraction.adapters.mock_his import MockHISDataSource
from extraction.adapters.portal_his import PortalHISDataSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import DEFAULT_TECHNIQUES
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.techniques.unconstrained import UnconstrainedExtractionTechnique
from interop.layers import HISLayer
from interop.normalise import audit, normalise
from tools.mock_portal.serve import BackgroundPortal

TASKS = [
    ExtractionTask(
        task_id="patient-summary",
        purpose=Purpose.CARE_COORDINATION,
        needed=[
            LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "date_of_birth", "sex"]),
            LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis", "medication", "allergy"]),
        ],
    ),
    ExtractionTask(
        task_id="ward-census",
        purpose=Purpose.CARE_COORDINATION,
        needed=[
            LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "admission_ward"]),
            LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["encounter_datetime"]),
        ],
    ),
    ExtractionTask(
        task_id="appointment-reminder",
        purpose=Purpose.PATIENT_REGISTRATION,
        needed=[
            LayerFields(
                layer=HISLayer.PATIENT_ADMINISTRATION,
                fields=["mrn", "full_name", "phone", "admission_datetime"],
            ),
        ],
    ),
]

ASSIST = [
    (StaffRole.RECEPTION, ["register a new patient", "Priya Raman", "1988-03-14", "+91-9800000012"]),
    (StaffRole.NURSE, ["look up the diagnosis", "MRN2867825"]),
    (StaffRole.ADMINISTRATOR, ["raise the bill", "MRN2867825", "ENC-20260912-07"]),
    (StaffRole.RECEPTION, ["what is the patient's diagnosis"]),
]


def stage(n: int, title: str) -> None:
    print(present.rule())
    print(f"[{n}] {title}")
    print()


def _load_map(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    import json
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: v for k, v in data.get("map", data).items() if v}


def run_downstream(scraper, pages: dict[str, str], dataset_note: str) -> None:
    """Stages 3-6: identical whatever the source was."""

    stage(3, "BENCHMARK -- three techniques; same seven rules; real cost")
    result = run_benchmark(DEFAULT_TECHNIQUES, TASKS, scraper, dataset_note=dataset_note)
    print(result.render_table())
    print()
    name = "benchmark-portal" if isinstance(scraper, PortalHISDataSource) else "benchmark-dataset"
    print(present.wrote(result.to_json_file(name=name)))
    print(present.wrote(result.to_markdown_file(name=name)))

    stage(4, "NORMALISE -- HL7 v2 / FHIR on the way out; identifiers pseudonymised, and audited")
    output = CompliantExtractionTechnique().extract(scraper, TASKS[0])
    baseline = UnconstrainedExtractionTechnique().extract(scraper, TASKS[0])
    for label, out in (("compliance-aware", output), ("baseline", baseline)):
        shaped = normalise(out)
        print(f"  {label}:")
        for line in shaped.render_summary().split("\n"):
            print(f"    {line}")
        print(f"    audit: {audit(out, shaped).one_line()}")
        print()
    print("  one registration record from the compliance-aware export:")
    print(normalise(output).sample(HISLayer.PATIENT_ADMINISTRATION))

    stage(5, "PURPOSE -- the same pull, judged under every purpose")
    matrix = score_across_purposes(output.run, output.records)
    print(matrix.render_table())

    stage(6, "ASSIST -- one question per role" + ("; steps land on the pages found in [2]" if pages else ""))
    for role, lines in ASSIST:
        session = Session(role, navigation=pages or None)
        reply = None
        for line in lines:
            print(f"  {role.value:<13} > {line}")
            reply = session.respond(line)
        assert reply is not None
        first, *rest = reply.text.split("\n")
        print(f"  assistant     : {first}")
        for extra in rest:
            print(f"                  {extra}")
        if reply.kind == ReplyKind.DECLINED:
            print("  (declined before asking for any detail)")
        print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--page-size", type=int, default=15)
    parser.add_argument("--latency-ms", type=int, default=0)
    parser.add_argument("--show", action="store_true", help="run the browser visibly")
    parser.add_argument("--dataset", help="directory of exported CSV/Excel files (real or synthetic)")
    parser.add_argument("--column-map", help="JSON header -> field map for --dataset")
    parser.add_argument("--portal", help="URL of an external portal instead of the local fixture")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("--aliases", help="JSON header -> field map for --portal")
    args = parser.parse_args()

    print(present.banner("End-to-end: source -> scrape -> DPDP benchmark -> export -> purpose -> assistant"))
    started = time.perf_counter()

    if args.dataset:
        stage(1, "DATASET -- an exported hospital dataset, handling checks enforced")
        scraper = DatasetHISDataSource(args.dataset, column_map=_load_map(args.column_map))
        print(f"  {args.dataset}")
        stage(2, "UNDERSTAND -- what the adapter made of the files")
        print(scraper.describe())
        run_downstream(scraper, {}, f"dataset {args.dataset}")

    elif args.portal:
        if not (args.user and args.password):
            parser.error("--portal needs --user and --password")
        stage(1, "PORTAL -- an external portal we do not control")
        print(f"  {args.portal}   account {args.user}")
        stage(2, "DISCOVER -- a browser logs in and works out what is where")
        scraper = PortalHISDataSource(
            args.portal, args.user, args.password, headless=not args.show,
            field_aliases=_load_map(args.aliases),
        )
        print(scraper.navigation.render_table())
        print()
        print(present.wrote(scraper.navigation.to_json_file()))
        run_downstream(scraper, scraper.navigation.agent_pages(), f"portal {args.portal}")
        scraper.close()

    else:
        source = MockHISDataSource(records_per_layer=args.records, seed=args.seed)
        with BackgroundPortal(source, page_size=args.page_size, latency_ms=args.latency_ms) as portal:
            stage(1, "PORTAL -- a login-gated HIS portal, served locally")
            print(f"  {portal.url}/   account {portal.username} / {portal.password}")
            print(f"  {args.records} records per module, {args.page_size} per page, "
                  f"{args.latency_ms} ms latency; robots.txt disallows all")

            stage(2, "DISCOVER -- a browser logs in and works out what is where")
            scraper = PortalHISDataSource(
                portal.url, portal.username, portal.password, headless=not args.show
            )
            print(scraper.navigation.render_table())
            print()
            print(present.wrote(scraper.navigation.to_json_file()))
            run_downstream(scraper, scraper.navigation.agent_pages(),
                           f"portal, {args.records} records/module, seed {args.seed}")
            scraper.close()

    print(present.rule())
    print(
        f"Done in {time.perf_counter() - started:.1f}s. Every stage ran for real: a source that was\n"
        f"read as a stranger would read it, three scrapers scored on identical rules with\n"
        f"measured cost, exports shaped to HL7 v2 and FHIR with identifiers pseudonymised\n"
        f"and audited, one pull judged under three purposes, and an assistant whose\n"
        f"refusals come from the same policy table."
    )


if __name__ == "__main__":
    main()
