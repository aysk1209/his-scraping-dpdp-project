"""Build Review-II.pptx from Review-I.pptx, keeping the institutional template intact.

    python tools/build_review_deck.py            # writes Review-II.pptx beside Review-I.pptx

The VIT/SENSE template's design is immutable, so this script never adds a slide
layout, moves a logo, or changes a font. It copies the Review-I deck and rewrites
the *content* of the existing text boxes and tables -- cloning each box's own
paragraph formatting for headings and bullets -- and replaces the two screenshot
pictures on the results slides with real, editable tables in the template's
colours. Slide 1 is the scanned, guide-signed title slide: the team replaces it
with the Review-II scan by hand, as before.

Needs ``python-pptx`` (authoring tool only; not a project dependency).
"""

from __future__ import annotations

import copy
import shutil
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Review-I.pptx"
TARGET = ROOT / "Review-II.pptx"

NAVY = RGBColor(0x1D, 0x2F, 0x82)
BLACK = RGBColor(0, 0, 0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY = RGBColor(0xBF, 0xBF, 0xBF)


# --------------------------------------------------------------------------- #
# helpers that respect the template
# --------------------------------------------------------------------------- #

def shape_named(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    raise KeyError(f"{name!r} not on slide")


def _set_paragraph_text(p_el, text):
    """Keep the paragraph's first run (its formatting); replace its text; drop the rest."""

    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    runs = p_el.findall("a:r", ns)
    for extra in runs[1:]:
        p_el.remove(extra)
    for br in p_el.findall("a:br", ns):
        p_el.remove(br)
    if runs:
        runs[0].find("a:t", ns).text = text
    else:  # pragma: no cover - template paragraphs always carry a run
        raise ValueError("template paragraph has no run to clone")


def rewrite_body(shape, blocks):
    """Rewrite a body text box as (heading, [bullets]) blocks.

    Clones the box's own level-0 heading paragraph and level-1 bullet paragraph
    so the result carries exactly the template's fonts, colours and bullets.
    """

    tf = shape.text_frame
    paragraphs = tf.paragraphs
    heading_tpl = next(p._p for p in paragraphs if p.level == 0 and p.runs)
    bullet_tpl = next(p._p for p in paragraphs if p.level == 1 and p.runs)
    body = tf._txBody
    for p in list(paragraphs):
        body.remove(p._p)
    for heading, bullets in blocks:
        if heading:
            h = copy.deepcopy(heading_tpl)
            _set_paragraph_text(h, heading)
            body.append(h)
        for bullet in bullets:
            b = copy.deepcopy(bullet_tpl)
            _set_paragraph_text(b, bullet)
            body.append(b)


def rewrite_plain(shape, lines, size=None):
    """Rewrite a text box whose paragraphs are all the same style."""

    tf = shape.text_frame
    tpl = next(p._p for p in tf.paragraphs if p.runs)
    body = tf._txBody
    for p in list(tf.paragraphs):
        body.remove(p._p)
    for line in lines:
        el = copy.deepcopy(tpl)
        _set_paragraph_text(el, line)
        body.append(el)
    if size is not None:
        for p in tf.paragraphs:
            for r in p.runs:
                r.font.size = Pt(size)


def set_cell(cell, text, *, size=None, bold=None, color=None):
    tf = cell.text_frame
    if tf.paragraphs and tf.paragraphs[0].runs:
        _set_paragraph_text(tf.paragraphs[0]._p, text)
        for extra in list(tf.paragraphs[1:]):
            tf._txBody.remove(extra._p)
        run = tf.paragraphs[0].runs[0]
    else:
        tf.text = text
        run = tf.paragraphs[0].runs[0]
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def fill_table(table, rows):
    """Write rows into an existing template table; extra template rows are blanked."""

    for r, values in enumerate(rows):
        for c, value in enumerate(values):
            set_cell(table.cell(r, c), value)
    for r in range(len(rows), len(table.rows)):
        for c in range(len(table.columns)):
            set_cell(table.cell(r, c), "")


def remove_shape(shape):
    shape._element.getparent().remove(shape._element)


def add_template_table(slide, left, top, width, height, rows, col_widths, *, body_size=11.5):
    """A new table styled like the template's: navy header, white bold text, black body."""

    n_rows, n_cols = len(rows), len(rows[0])
    gf = slide.shapes.add_table(n_rows, n_cols, Inches(left), Inches(top), Inches(width), Inches(height))
    table = gf.table
    for i, w in enumerate(col_widths):
        table.columns[i].width = Inches(w)
    for r, values in enumerate(rows):
        for c, value in enumerate(values):
            cell = table.cell(r, c)
            cell.text = value
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if r == 0 else WHITE
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.name = "Calibri"
                    run.font.size = Pt(12 if r == 0 else body_size)
                    run.font.bold = (r == 0)
                    run.font.color.rgb = WHITE if r == 0 else BLACK
    return gf


def add_note_box(slide, left, top, width, height, lines, *, size=11.5, color=BLACK, bold_first=False):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = p.add_run()
        run.text = line
        run.font.name = "Calibri"
        run.font.size = Pt(size)
        run.font.color.rgb = color
        if bold_first and i == 0:
            run.font.bold = True
    return tb


# --------------------------------------------------------------------------- #
# content
# --------------------------------------------------------------------------- #

def build() -> Path:
    shutil.copyfile(SOURCE, TARGET)
    prs = Presentation(TARGET)
    s = prs.slides

    # ---- slide 2: Problem Statement & Background (tightened, same shape) ----
    rewrite_body(shape_named(s[1], "Text 2"), [
        ("Problem Statement:", [
            "Hospital Information Systems hold highly sensitive personal data, yet the techniques used to extract "
            "data from them are judged on speed, robustness and coverage — never on data-protection compliance.",
            "Under the DPDP Act 2023, compliance is treated as a legal afterthought bolted on after extraction, "
            "not a property the technique is designed and measured against.",
        ]),
        ("Background & Significance:", [
            "HIS platforms are heterogeneous and frequently updated; staff adapt to them with little support, and "
            "every extraction touches identifiers, clinical, contact and financial data of real patients.",
            "The Act makes lawful basis, purpose limitation, minimisation, storage limitation, safeguards, notice "
            "and accountability enforceable obligations — each one a checkable property of an extraction run.",
        ]),
        ("Existing Solutions:", [
            "Rule / wrapper scrapers (fast, brittle), headless-browser automation (robust, expensive), and LLM-driven "
            "extraction agents (cross-domain, but evaluated on coverage alone).",
            "Compliance guidance exists only as qualitative checklists; no technique reports a compliance score.",
        ]),
        ("Limitations / Research Gap:", [
            "Because no technique is scored on compliance, techniques cannot be compared on it, and \"compliant\" "
            "stays an assertion rather than a measurement.",
            "Our gap: make DPDP compliance a benchmarkable, per-technique property — scored on identical rules, "
            "paired with cost, and verified against what the extraction actually produces.",
        ]),
    ])

    # ---- slide 5: Proposed Solution & Methodology ----
    rewrite_body(shape_named(s[4], "Text 2"), [
        ("Proposed Solution:", [
            "A DPDP-compliance benchmarking pipeline: every extraction technique is scored on the same seven "
            "principle-based rules and metered for cost, so compliance is a measured property of a technique.",
            "One policy table — three non-nested purposes, roles derived from purposes and interoperability "
            "artefacts — read by three blocks: it scores the extraction, gates the HL7/FHIR export, and gates what a "
            "staff assistant may say. One project, not two.",
        ]),
        ("Methodology (working blocks):", [
            "Acquisition — any source behind one HISDataSource interface: synthetic records, a login-gated portal "
            "scraped by a real browser, or a hospital export read through a column map.",
            "Semantics — a catalogue maps field → HIS layer → DPDP category; a module's layer is inferred from its "
            "field names, never from its label. Extraction — a technique pulls and declares a manifest; records are "
            "scored by category, never by value.",
            "Scoring — 7 rules → 0–1 score with findings; benchmark on compliance × cost (excess ratio, coverage, "
            "real page loads); one pull re-judged under every purpose. Export — pseudonymise when declared → HL7 v2 "
            "/ FHIR → audit the artefacts for raw identifiers.",
        ]),
        ("Project Scope:", [
            "In: extraction techniques, the compliance framework and benchmark, interop export with audit, the "
            "rule-based staff assistant, a mock portal fixture, a dataset adapter for the hospital export.",
            "Out: deployment; live HIS access (the adapter is built and waiting); an LLM agent — the assistant has "
            "no model and no training, by design.",
        ]),
    ])

    # ---- slide 6: Methodology — Rules, Scoring & Extraction ----
    rewrite_body(shape_named(s[5], "Text 2"), [
        ("Seven executable DPDP rules, each a distinct check, each naming its principle:", [
            "DM-01 minimisation (extracted categories ⊆ purpose scope) · LB-01 lawful basis (declared, recognised, "
            "referenced) · SL-01 storage limitation (retention ≤ purpose ceiling + deletion mechanism) · SS-01 "
            "safeguards (TLS, at-rest, access control, pseudonymisation when required).",
            "PL-01 purpose limitation (specified, recognised, onward uses assessed for compatibility) · NT-01 notice "
            "(recorded, covers the purpose) · AC-01 accountability (audit log, named party, processing record).",
        ]),
        ("Three purposes, pairwise non-nested — \"out of scope\" means not necessary for this purpose:", [
            "care_coordination: clinical, not financial/contact, 90 d · billing_settlement: financial + contact, not "
            "clinical, 365 d · patient_registration: contact + demographics, neither clinical nor financial, 180 d.",
        ]),
        ("Three techniques scored on identical terms:", [
            "compliance-aware (ours) — pulls what the purpose makes necessary, full manifest, pseudonymises. "
            "Morality model — pulls what does not feel private, refuses what does, whatever the purpose; declares by "
            "instinct. Unconstrained baseline — every field of every module, no manifest.",
        ]),
        ("Cost and the role gate:", [
            "Excess ratio = fields pulled ÷ fields required — both a cost and the minimisation overreach DM-01 "
            "penalises; coverage guards against pulling nothing; page loads come from the real browser.",
            "A role's scope = (categories lawful under its purposes) ∩ (categories in the HL7/FHIR/DICOM/11073 "
            "artefacts it handles); authorise() checks PL-01 → DM-01 → SS-01 and names the rule when it declines.",
        ]),
    ])

    # ---- slide 7: Tools & Technologies ----
    fill_table(shape_named(s[6], "Tools Table").table, [
        ["Technology", "Where it is used", "Why this choice"],
        ["Python 3.10+", "The entire pipeline — data, extraction, rules, benchmark, export, assistant, portal fixture",
         "Standard for research and scraping; one language end to end."],
        ["Pydantic v2", "Manifest, rules, per-layer schemas, benchmark and purpose-matrix artefacts",
         "Malformed manifests fail at the boundary; artefacts serialise for the report."],
        ["Playwright (Chromium)", "Tier-2 scraping of the login-gated portal: form login, crawl, tables, pagination; counts page loads",
         "A real browser gives real cost; transfers to a real portal as selectors + label aliases."],
        ["Flask 3", "The mock HIS portal — a fixture built as a system we do not control",
         "One dependency; sessions and templating built in; nothing downstream depends on it."],
        ["Faker · pandas", "Synthetic records; CSV/Excel export reader (dataset adapter, column-mapped)",
         "No real patients; the hospital export becomes a column map, not new code."],
        ["pytest", "219 tests: rules, purposes, roles, techniques, adapters, shaping, assistant, browser-driven Tier-2",
         "The rules and gates are the contribution; each is tested in both directions."],
        ["HL7 v2 · FHIR R4 (hand-rolled)", "Export shaping per layer incl. AuditEvent; DICOM / 11073 stubs",
         "No vendor libraries; shaping adds nothing that was not extracted."],
    ])
    rewrite_plain(shape_named(s[6], "Text 41"), [
        "Where this runs: everything executes locally — the portal on localhost, the browser headless, all data "
        "synthetic. One command (scripts/run_pipeline.py) runs the six stages in 30–40 s. No real hospital "
        "system or real patient data is touched; the adapter for the real export is built and waiting.",
    ])

    # ---- slide 8: Work Completed & Timeline ----
    rewrite_body(shape_named(s[7], "Text 2"), [
        ("Work completed (94 of 100 on the team's ledger — everything not requiring live access):", [
            "Compliance: 7 rules · 3 non-nested purposes · role gate derived from purposes × interop artefacts · "
            "purpose matrix · pseudonymisation on export with an audit of what actually left.",
            "Extraction: one adapter interface · three techniques · cost metering · Tier-2 Playwright scraper with a "
            "crawl-discovered navigation map · dataset adapter with column map · label→field aliases · mock portal.",
            "Interop: five-layer catalogue and schemas · HL7 v2 (ADT/ORM/ORU/DFT) · FHIR (10 resources incl. "
            "AuditEvent). Assistant: 13 functions, three roles, gate before collecting, steps on discovered pages.",
            "One command runs the whole chain, live, in 30–40 s. 219 passing tests.",
        ]),
        ("Remaining:", [
            "Project report and publication manuscript (the compliance chapters need no real data). Real hospital "
            "dataset → a column map. Section-number mapping of each rule to the Act, at report time as planned.",
        ]),
        ("Timeline to Review-III:", [
            "Review-II (now): the pipeline end to end · next: report drafting, real-data integration when the export "
            "arrives · Review-III: full report, manuscript, and results on real data beside the synthetic results.",
        ]),
    ])

    # ---- slide 9: Results — the benchmark ----
    rewrite_plain(shape_named(s[8], "Text 20"), [
        "Three techniques, three extraction tasks, the same login-gated portal scraped by a real browser "
        "(30 records per module); every run scored on the identical seven rules; cost measured as real page loads.",
        "They differ only in how they treat personal data — the compliance-aware technique is not faster or "
        "cleverer, it asks what the purpose makes necessary and declares what it did.",
    ])
    fill_table(shape_named(s[8], "Benchmark Table").table, [
        ["Technique", "Compliance", "Cost", "Behaviour"],
        ["compliance-aware (ours)", "1.000  ·  7 / 7 rules", "excess 1.00 · coverage 1.00 · ~100 pages",
         "Pulls what the purpose makes necessary; full manifest; identifiers pseudonymised on export."],
        ["morality (privacy by instinct)", "0.484  ·  2 / 7 rules", "excess 0.85 · coverage 0.85 · ~100 pages",
         "Refuses what feels private (names, contact, money) whatever the purpose; takes MRN and DOB freely; "
         "consent assumed, no notice, no retention."],
        ["unconstrained (baseline)", "0.135  ·  0 / 7 rules", "excess 7.15 · coverage 1.00 · ~480 pages",
         "Every field of every module; no purpose, no manifest, TLS only."],
    ])
    rewrite_plain(shape_named(s[8], "Text 22"), [
        "The baseline loads about five times the pages for the same coverage: its surplus is exactly the overreach "
        "DM-01 penalises, so compliance and cost move together rather than trading off.",
        "The morality model is the cheapest — and the cheapness is its failure: coverage 0.85 because it refused a "
        "name and a phone number that an appointment reminder lawfully needs. Privacy by instinct fails in both "
        "directions; only a purpose-bound technique gets both right.",
    ])

    # ---- slide 10: Results (contd.) — purpose matrix + export audit ----
    rewrite_plain(shape_named(s[9], "Text 20"), [
        "The same extraction, judged under every purpose. Records, manifest and rules are identical down each "
        "row — only what the data was for changes. Compliance is a property of a pull and its purpose together.",
        "And the export is audited, not trusted: the compliance-aware manifest claims pseudonymisation; we searched "
        "what actually left for the raw identifiers.",
    ])
    remove_shape(shape_named(s[9], "Picture 5"))
    add_template_table(s[9], 0.6, 2.7, 12.13, 1.5, [
        ["Extraction (care pull: MRN, DOB, sex, diagnosis, medication, allergy)", "under care_coordination",
         "under billing_settlement", "under patient_registration"],
        ["compliance score · rules passed", "1.000  ·  7 / 7", "0.833  ·  5 / 7", "0.881  ·  5 / 7"],
        ["why", "lawful for this purpose", "out of scope: clinical, quasi-identifier; notice does not cover it",
         "out of scope: clinical; notice does not cover it"],
    ], [4.6, 2.2, 2.9, 2.43])
    add_template_table(s[9], 0.6, 4.55, 12.13, 1.3, [
        ["Export audit (HL7 v2 + FHIR)", "Pseudonymisation", "Raw identifiers found in the export"],
        ["compliance-aware (ours)", "declared → applied (HMAC tokens, PSN-…)", "0 of 120 · 180 artefacts checked"],
        ["unconstrained (baseline)", "not declared → raw", "120 of 120 · 510 artefacts checked"],
    ], [4.6, 3.6, 3.93])
    add_note_box(s[9], 0.7, 6.0, 11.9, 0.9, [
        "Care may see clinical data and not billing data; billing may see billing data and not clinical data. "
        "Neither purpose is stricter — \"out of scope\" means not necessary for this purpose. The tokens in the "
        "export are keyed hashes: stable within one export, unlinkable across exports, not reversible.",
    ], size=11.5)

    # ---- slide 11: Results — discovery and the assistant ----
    sh = shape_named(s[10], "Text 1")
    rewrite_plain(sh, ["Results — Discovery & the Staff Assistant"])
    rewrite_plain(shape_named(s[10], "Text 20"), [
        "The scraper is never told the portal's layout. It crawls from the home page and infers each module's HIS "
        "layer from the field names it finds — the URL says \"registration\", the scraper concludes patient "
        "administration. Point it at a differently-named portal and the map re-derives itself.",
        "The assistant has no model. It recognises a fixed function, checks the role gate before asking for any "
        "detail, and places every step on the page the crawler found a minute earlier.",
    ])
    remove_shape(shape_named(s[10], "Picture 6"))
    add_template_table(s[10], 0.6, 2.75, 12.13, 1.9, [
        ["Module (as the portal names it)", "Path", "Pages", "Inferred HIS layer", "Confidence"],
        ["Patient Registration", "/m/registration/", "2", "patient_administration", "100%"],
        ["Clinical Records", "/m/clinical/", "2", "clinical_ehr", "100%"],
        ["Departmental Orders", "/m/departments/", "2", "ancillary_departmental", "100%"],
        ["Billing & Accounts", "/m/billing/", "2", "administrative_financial", "100%"],
        ["Audit Log", "/m/integration/", "2", "infrastructure_integration", "100%"],
    ], [3.4, 2.2, 1.0, 3.6, 1.93], body_size=11)
    add_note_box(s[10], 0.7, 4.85, 11.9, 2.1, [
        "reception > what is the patient's diagnosis",
        "assistant : I can't walk you through how to look up a patient's diagnosis as reception.",
        "            reception has no lawful purpose to act under 'care_coordination'; its purposes are "
        "billing_settlement, patient_registration.   [PL-01 — DPDP Act 2023 - purpose limitation]",
        "            This is something nurse can do; please hand it to them.        (declined before asking for any detail)",
        "The refusal comes from the same policy table that scored the benchmark. Nurse asking the same question is "
        "walked through it: [clinical_ehr / Condition / /m/clinical/].",
    ], size=11)

    prs.save(TARGET)
    return TARGET


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")
    print("Slide 1 is still the Review-I scan: replace it with the guide-signed Review-II title slide.")
