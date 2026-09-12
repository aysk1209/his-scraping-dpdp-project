"""The whole pipeline, end to end, in one command.

    python scripts/run_pipeline.py                  # 30 records/layer, ~40 s
    python scripts/run_pipeline.py --records 200    # more pages, longer run
    python scripts/run_pipeline.py --show           # watch the browser work

Five stages, each real:

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--page-size", type=int, default=15)
    parser.add_argument("--latency-ms", type=int, default=0)
    parser.add_argument("--show", action="store_true", help="run the browser visibly")
    args = parser.parse_args()

    print(present.banner("End-to-end: portal -> scrape -> DPDP benchmark -> purpose -> assistant"))
    started = time.perf_counter()

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

        stage(3, "BENCHMARK -- three techniques scrape it; same seven rules; real cost")
        result = run_benchmark(
            DEFAULT_TECHNIQUES, TASKS, scraper,
            dataset_note=f"portal, {args.records} records/module, seed {args.seed}",
        )
        print(result.render_table())
        print()
        print(present.wrote(result.to_json_file(name="benchmark-portal")))
        print(present.wrote(result.to_markdown_file(name="benchmark-portal")))

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

        stage(6, "ASSIST -- one question per role; steps land on the pages found in [2]")
        pages = scraper.navigation.agent_pages()
        for role, lines in ASSIST:
            session = Session(role, navigation=pages)
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

        scraper.close()

    print(present.rule())
    print(
        f"Done in {time.perf_counter() - started:.1f}s. Every stage ran for real: a served\n"
        f"portal, a browser that logged in and crawled it, three scrapers scored on\n"
        f"identical rules with real page loads as cost, one pull judged under three\n"
        f"purposes, exports shaped to HL7 v2 and FHIR with identifiers pseudonymised\n"
        f"and audited, and an assistant whose refusals come from the same policy table."
    )


if __name__ == "__main__":
    main()
