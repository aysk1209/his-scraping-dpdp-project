"""Build Review-II.pptx on the institution's Review-2 template.

    python tools/build_review_deck.py            # writes Review-II.pptx from "Review-2 Template.pptx"

The template's design is immutable, so this script never adds a layout, moves a
logo, or changes a font. It fills the template's own text boxes by cloning the
template's paragraph styles, fills its literature table, duplicates the
literature and results slides where the content needs more room, draws the
working-blocks diagram as shapes on the (deliberately empty) architecture slide,
and renumbers the page-number boxes. Slide 1 stays the template's instruction
slide until the team replaces it with the guide-signed scan, as the template says.

Content facts (dates, marks, focus, mark split) come from the template itself.

Needs ``python-pptx`` (authoring tool only; not a project dependency).
"""

from __future__ import annotations

import copy
import shutil
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "Review-2 Template.pptx"
REVIEW_I = ROOT / "Review-I.pptx"
TARGET = ROOT / "Review-II.pptx"

NAVY = RGBColor(0x1D, 0x2F, 0x82)
BLACK = RGBColor(0, 0, 0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY = RGBColor(0x80, 0x80, 0x80)
LIGHT = RGBColor(0xEE, 0xF0, 0xF8)

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


# --------------------------------------------------------------------------- #
# template-respecting helpers
# --------------------------------------------------------------------------- #

def shape_named(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    raise KeyError(f"{name!r} not on slide")


def _set_paragraph_text(p_el, text):
    runs = p_el.findall(f"{A}r")
    for extra in runs[1:]:
        p_el.remove(extra)
    for br in p_el.findall(f"{A}br"):
        p_el.remove(br)
    runs[0].find(f"{A}t").text = text
    return runs[0]


def _run_font(run_el, size=None, bold=None, color=None):
    rpr = run_el.find(f"{A}rPr")
    if rpr is None:
        rpr = run_el.makeelement(f"{A}rPr", {})
        run_el.insert(0, rpr)
    if size is not None:
        rpr.set("sz", str(int(size * 100)))
    if bold is not None:
        rpr.set("b", "1" if bold else "0")
    if color is not None:
        for old in rpr.findall(f"{A}solidFill"):
            rpr.remove(old)
        fill = rpr.makeelement(f"{A}solidFill", {})
        clr = fill.makeelement(f"{A}srgbClr", {"val": str(color)})
        fill.append(clr)
        rpr.insert(0, fill)


class Styles:
    """Paragraph templates lifted from the template's review-info slide."""

    def __init__(self, prs):
        tf = shape_named(prs.slides[2], "Text 2").text_frame
        self.heading = copy.deepcopy(next(p._p for p in tf.paragraphs if p.level == 0 and p.runs))
        self.bullet = copy.deepcopy(next(p._p for p in tf.paragraphs if p.level == 1 and p.runs))


def rewrite_body(shape, blocks, styles, *, heading_size=15, bullet_size=12.5):
    """Fill a body box with (heading, [bullets]) blocks in the template's styles."""

    body = shape.text_frame._txBody
    for p in list(shape.text_frame.paragraphs):
        body.remove(p._p)
    for heading, bullets in blocks:
        if heading:
            h = copy.deepcopy(styles.heading)
            run = _set_paragraph_text(h, heading)
            _run_font(run, size=heading_size, bold=True, color=NAVY)
            body.append(h)
        for bullet in bullets:
            b = copy.deepcopy(styles.bullet)
            run = _set_paragraph_text(b, bullet)
            _run_font(run, size=bullet_size, bold=False, color=BLACK)
            body.append(b)


def rewrite_plain(shape, lines, *, size=None):
    tf = shape.text_frame
    tpl = copy.deepcopy(next(p._p for p in tf.paragraphs if p.runs))
    body = tf._txBody
    for p in list(tf.paragraphs):
        body.remove(p._p)
    for line in lines:
        el = copy.deepcopy(tpl)
        run = _set_paragraph_text(el, line)
        if size is not None:
            _run_font(run, size=size)
        body.append(el)


def set_cell(cell, text, *, size=None):
    tf = cell.text_frame
    if tf.paragraphs and tf.paragraphs[0].runs:
        run = _set_paragraph_text(tf.paragraphs[0]._p, text)
        for extra in list(tf.paragraphs[1:]):
            tf._txBody.remove(extra._p)
    else:
        tf.text = text
        run = tf.paragraphs[0].runs[0]._r
    if size is not None:
        _run_font(run, size=size)


def fill_table(table, rows, *, size=None):
    for r, values in enumerate(rows):
        for c, value in enumerate(values):
            set_cell(table.cell(r, c), value, size=size)
    for r in range(len(rows), len(table.rows)):
        for c in range(len(table.columns)):
            set_cell(table.cell(r, c), "")


def duplicate_slide(prs, index):
    """Append a copy of slide ``index`` (shapes and image relationships) and return it."""

    src = prs.slides[index]
    dst = prs.slides.add_slide(src.slide_layout)
    for sh in list(dst.shapes):
        sh._element.getparent().remove(sh._element)
    rid_map = {}
    for rel in src.part.rels.values():
        if "image" in rel.reltype:
            rid_map[rel.rId] = dst.part.relate_to(rel._target, rel.reltype)
    for sh in src.shapes:
        el = copy.deepcopy(sh._element)
        for blip in el.iter(f"{A}blip"):
            old = blip.get(f"{R}embed")
            if old in rid_map:
                blip.set(f"{R}embed", rid_map[old])
        dst.shapes._spTree.insert_element_before(el, "p:extLst")
    return dst


def move_slide(prs, slide, new_index):
    sldIdLst = prs.slides._sldIdLst
    ids = list(sldIdLst)
    el = next(e for e in ids if prs.slides.part.related_part(e.rId) is slide.part) if hasattr(prs.slides.part, "related_part") else None
    if el is None:
        # fall back: match by slide id order (the appended slide is last)
        el = ids[-1]
    sldIdLst.remove(el)
    sldIdLst.insert(new_index, el)


def renumber(prs):
    for n, slide in enumerate(prs.slides, start=1):
        for sh in slide.shapes:
            if sh.name == "Text 0" and sh.has_text_frame:
                rewrite_plain(sh, [str(n)])


def add_table(slide, left, top, width, height, rows, col_widths, *, body_size=11.5, header_size=12):
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
                    run.font.size = Pt(header_size if r == 0 else body_size)
                    run.font.bold = (r == 0)
                    run.font.color.rgb = WHITE if r == 0 else BLACK
    return gf


def add_text(slide, left, top, width, height, lines, *, size=11.5, color=BLACK, bold_first=False,
             font="Calibri", align=None):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if align is not None:
            p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.bold = bool(bold_first and i == 0)
    return tb


def add_box(slide, left, top, width, height, title, sub=None, *, fill=WHITE, size=11.5):
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    box.line.color.rgb = NAVY
    box.line.width = Pt(1.25)
    box.shadow.inherit = False
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.06)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = title
    r.font.name = "Calibri"
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = NAVY
    if sub:
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run()
        r2.text = sub
        r2.font.name = "Calibri"
        r2.font.size = Pt(size - 2.5)
        r2.font.color.rgb = BLACK
    return box


def add_arrow(slide, x1, y1, x2, y2):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = NAVY
    c.line.width = Pt(1.5)
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement(f"{A}tailEnd", {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return c


# --------------------------------------------------------------------------- #
# content
# --------------------------------------------------------------------------- #

LIT_ROWS = [
    ["1", "Ruchitaa et al., 2023", "Web Scraping Tools and Techniques: A Brief Survey — ICITIIT",
     "Survey / taxonomy of scraping tools and methods", "Broad catalogue; no domain-specific (HIS) use and no compliance axis"],
    ["2", "Huang et al., 2024", "AutoScraper: A Progressive Understanding Web Agent — EMNLP",
     "Two-stage LLM agent using HTML hierarchy + cross-page similarity; executability metric",
     "SOTA scraper generation, but evaluated only on executability / coverage — no data protection"],
    ["3", "Mansour et al., 2026", "AXE: Low-Cost Cross-Domain Web Structured Information Extraction — arXiv",
     "DOM-tree pruning + Grounded XPath Resolution feeding a 0.6B LLM; zero-shot",
     "F1 88.1% on SWDE at low cost; no compliance modelling, not applied to credentialed domains"],
    ["4", "Bohra et al., 2025", "WebLists: Structured Extraction from Interactive Sites (BardeenAgent) — arXiv",
     "200-task benchmark; agent converts execution into replayable programs",
     "Recall 31%→66%; regulated / enterprise contexts and privacy risk left unaddressed"],
    ["5", "Wang et al., 2026", "Co-Scraper: Query-Aware DOM Pruning and Reusable Scraper Synthesis — arXiv",
     "Two-stage query-aware pruning + extraction-strategy induction",
     "F1 94.78% SWDE, ~90% reuse; optimises efficiency only — no purpose-limitation notion"],
    ["6", "Gundelach et al., 2025", "Detecting Bot Detection: Prevalence, Techniques, Implications — arXiv",
     "Systematic review (2020–25) of bot-detection at top security / web venues",
     "Maps the detection landscape; authenticated / credentialed portal scraping under-studied"],
    ["7", "ACM IMC, 2025", "Scrapers Selectively Respect robots.txt Directives — large-scale study",
     "Internet-scale measurement of robots.txt compliance in the wild",
     "Compliance observed after the fact, never designed into the technique"],
    ["8", "Purnawan & Surendro, 2016", "Building Enterprise Architecture for Hospital Information System — ICoICT",
     "Enterprise-architecture modelling of HIS structure",
     "Useful layer model; predates LLM extraction, no data-egress / compliance view"],
    ["9", "Interoperability review, 2025", "A Critical Review of Health Data Interoperability Standards: FHIR, HL7 and Beyond",
     "Critical review of HL7 / FHIR and related standards",
     "Interoperability ≠ compliant extraction; standards are silent on lawful scraping"],
    ["10", "Discover Public Health, 2025", "Significance of the DPDP Act 2023 for the Healthcare Industry",
     "Doctrinal analysis of DPDP obligations for healthcare entities",
     "Legal analysis only; no technical or measurable operationalisation"],
    ["11", "npj Digital Medicine, 2025", "Digital Data Protection in Indian Medical Research and Healthcare",
     "Synthesis of challenges and recommendations",
     "Recommendations not translated into checkable controls on data-collection pipelines"],
    ["12", "Brown et al., 2025", "Web Scraping for Research: Legal, Ethical, Institutional and Scientific Considerations — Big Data & Society",
     "Multi-dimensional qualitative framework (contract, CFAA, IP, privacy, IRB, validity)",
     "A checklist, not a scored per-technique benchmark"],
]

REFERENCES = [
    '[1] R. N. R. Ruchitaa, S. Nandhakumar Raj, and M. Vijayalakshmi, "Web Scrapping Tools and Techniques: A Brief Survey," in Proc. 2023 4th Int. Conf. Innovative Trends in Information Technology (ICITIIT), 2023.',
    '[2] W. Huang et al., "AutoScraper: A Progressive Understanding Web Agent for Web Scraper Generation," in Proc. 2024 Conf. Empirical Methods in Natural Language Processing (EMNLP), Miami, FL, USA, 2024, pp. 2371–2389.',
    '[3] A. Mansour, K. W. Alshaer, and M. Elsaban, "AXE: Low-Cost Cross-Domain Web Structured Information Extraction," arXiv:2602.01838, 2026.',
    '[4] A. Bohra et al., "WebLists: Extracting Structured Information from Complex Interactive Websites Using Executable LLM Agents," arXiv:2504.12682, 2025.',
    '[5] S. Wang, J. Qiu, W. Zhang, and C. He, "Co-Scraper: Query-Aware DOM Pruning and Reusable Scraper Synthesis for Lightweight Web Data Extraction," arXiv:2606.14821, 2026.',
    '[6] R. Gundelach, M. Mühlhauser, and D. Herrmann, "Detecting Bot Detection: Prevalence, Techniques, and Implications for Web Measurement Research," arXiv:2606.14525, 2025.',
    '[7] "Scrapers Selectively Respect robots.txt Directives: Evidence From a Large-Scale Empirical Study," in Proc. 2025 ACM Internet Measurement Conf. (IMC), 2025.',
    '[8] D. A. Purnawan and K. Surendro, "Building Enterprise Architecture for Hospital Information System," in Proc. 2016 4th Int. Conf. Information and Communication Technology (ICoICT), Bandung, Indonesia, 2016.',
    '[9] "A Critical Review of Health Data Interoperability Standards: FHIR, HL7, and Beyond," 2025.',
    '[10] "Examining the Significance of the Digital Personal Data Protection Act, 2023 in the Context of the Healthcare Industry: A Comprehensive Analysis," Discover Public Health, 2025.',
    '[11] "Challenges and Recommendations for Enhancing Digital Data Protection in the Indian Medical Research and Healthcare Sector," npj Digital Medicine, 2025.',
    '[12] M. A. Brown, A. Gruen, G. Maldoff, S. Messing, Z. Sanderson, and M. Zimmer, "Web Scraping for Research: Legal, Ethical, Institutional, and Scientific Considerations," Big Data & Society, 2025.',
    '[13] The Digital Personal Data Protection Act, 2023, Act No. 22 of 2023, The Gazette of India, 11 Aug. 2023.',
]


def draw_architecture(slide):
    """The working-blocks diagram, as shapes, in the template's colours."""

    # Row 1: the chain
    y1 = 1.55
    add_box(slide, 0.6, y1, 2.2, 1.05, "A · Sources", "portal · export · synthetic\n(not ours to control)")
    add_arrow(slide, 2.8, y1 + 0.52, 3.15, y1 + 0.52)
    add_box(slide, 3.15, y1, 2.35, 1.05, "B · Acquisition", "one HISDataSource;\nbrowser / files / mock")
    add_arrow(slide, 5.5, y1 + 0.52, 5.85, y1 + 0.52)
    add_box(slide, 5.85, y1, 2.35, 1.05, "C · Semantics", "field → layer → DPDP\ncategory; infer_layer()")
    add_arrow(slide, 8.2, y1 + 0.52, 8.55, y1 + 0.52)
    add_box(slide, 8.55, y1, 2.55, 1.05, "D · Extraction", "task → technique →\nmanifest + records (metered)")

    # Row 2: the three consumers
    y2 = 3.45
    add_arrow(slide, 9.82, y1 + 1.05, 9.82, y2 - 0.02)
    add_box(slide, 3.15, y2, 2.35, 1.15, "E · Scoring", "7 rules · benchmark\ncompliance × cost · purpose matrix")
    add_box(slide, 5.85, y2, 2.35, 1.15, "F · Export", "pseudonymise → HL7 v2 /\nFHIR → audit the artefacts")
    add_box(slide, 8.55, y2, 2.55, 1.15, "G · Guidance", "recognise → gate →\ncollect → instruct")
    # fan-out from D to E and F via a horizontal bus
    add_arrow(slide, 9.82, y2 - 0.02, 9.82, y2)  # tiny stub to keep arrowheads consistent
    bus_y = y2 - 0.38
    slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(4.32), Inches(bus_y), Inches(9.82), Inches(bus_y)).line.color.rgb = NAVY
    add_arrow(slide, 4.32, bus_y, 4.32, y2)
    add_arrow(slide, 7.02, bus_y, 7.02, y2)

    # Row 3: policy, read by all three
    y3 = 5.35
    add_box(slide, 3.15, y3, 7.95, 0.95, "H · Policy — one table, three readers",
            "3 non-nested purposes · role = purposes ∩ interop artefacts · 7 principles (PL-01 → DM-01 → SS-01)",
            fill=LIGHT)
    for x in (4.32, 7.02, 9.82):
        add_arrow(slide, x, y3, x, y2 + 1.15)

    add_text(slide, 0.6, 3.45, 2.3, 2.85, [
        "Adapter boundary",
        "Nothing downstream of B knows which source it got. A new HIS is a new adapter, not a downstream rewrite.",
        "",
        "Why one project",
        "H scores the extraction (E), gates what leaves (F), and gates what a person may be told (G).",
    ], size=10.5, color=BLACK, bold_first=True)
    add_text(slide, 0.6, 6.45, 12.1, 0.5, [
        "Runs as one command: scripts/run_pipeline.py — portal → discover → benchmark → normalise + audit → purpose → assistant (30–40 s)."
    ], size=11, color=GREY)


def build() -> Path:
    shutil.copyfile(TEMPLATE, TARGET)
    prs = Presentation(TARGET)
    styles = Styles(prs)
    s = prs.slides

    # ---- slide 2: title slide fields ----
    rewrite_plain(shape_named(s[1], "Text 3"), ["AI-Driven HIS Management Agent with DPDP-Compliant Web Scraping"], size=26)
    rewrite_plain(shape_named(s[1], "Text 5"), ["Avanindra (23BLC1089) · Ananya (23BLC1017)"], size=13)
    rewrite_plain(shape_named(s[1], "Text 8"), ["Dr. Manoj Kumar, SENSE"])

    # ---- slide 4: Introduction & Problem Recap ----
    rewrite_body(shape_named(s[3], "Text 2"), [
        ("Problem recap:", [
            "Hospital Information Systems hold identifiers, clinical, contact and financial data of real patients; "
            "the techniques used to extract data from them are judged on speed, robustness and coverage — never on "
            "DPDP Act 2023 compliance. Compliance stays an assertion, so techniques cannot be compared on it.",
        ]),
        ("Objectives:", [
            "Make DPDP compliance a measured, per-technique property: every extraction scored on the same seven "
            "principle-based rules, paired with a reproducible cost measure, and verified against what the "
            "extraction actually produces.",
            "Show the whole chain running end to end — a credentialed portal scraped by a real browser, scored, "
            "exported to HL7 v2 / FHIR with identifiers pseudonymised and audited — and a rule-based staff assistant "
            "gated by the same policy.",
        ]),
        ("Refinements after Review-I feedback:", [
            "Processing time, as asked: a cost profile per technique — fields pulled, fetches, real browser page "
            "loads, excess ratio, coverage, wall-clock (deterministic metrics lead; wall-clock is hardware-dependent).",
            "The middle technique is now the morality model — privacy judged by instinct from a field's name, no "
            "concept of purpose — deliberately not DPDP-compliant; the hand-written baseline stands, as the panel "
            "agreed most deployed systems sit there.",
            "The assistant is rule-based: a fixed function registry, no LLM, no training — answering the Review-I "
            "question of how it is trained: it is not. Heterogeneity is answered by discovery: module layers are "
            "inferred from field names, never read from labels.",
        ]),
    ], styles, heading_size=15, bullet_size=12.5)

    # ---- slides 5, 5b: Detailed Literature Review (12 rows over two slides) ----
    lit_tbl = [sh for sh in s[4].shapes if getattr(sh, "has_table", False) and sh.has_table][0].table
    header = [c.text for c in lit_tbl.rows[0].cells]
    fill_table(lit_tbl, [header, *LIT_ROWS[:6]], size=11.5)
    rewrite_plain(shape_named(s[4], "Text 2"), [
        "References [1]–[6] on this slide, [7]–[12] on the next; full IEEE list on the References slide. "
        "The gap across all twelve: no technique reports a per-technique compliance score."
    ], size=11)
    lit2 = duplicate_slide(prs, 4)
    move_slide(prs, lit2, 5)
    rewrite_plain(shape_named(lit2, "Text 1"), ["Detailed Literature Review (contd.)"])
    lit2_tbl = [sh for sh in lit2.shapes if getattr(sh, "has_table", False) and sh.has_table][0].table
    fill_table(lit2_tbl, [header, *LIT_ROWS[6:12]], size=11.5)
    rewrite_plain(shape_named(lit2, "Text 2"), [
        "Research gap: scraping is evaluated on coverage and cost; healthcare-data law is analysed doctrinally; "
        "nothing between them scores a technique on compliance. [13] is the Act itself."
    ], size=11)

    # ---- slide 6 (now index 6): System Design & Architecture ----
    arch = s[6]
    assert shape_named(arch, "Text 1").text_frame.text.startswith("System Design")
    draw_architecture(arch)

    # ---- slide 7 (index 7): Implementation Details ----
    rewrite_body(shape_named(s[7], "Text 2"), [
        ("Modules developed and integrated (src/, 224 tests):", [
            "compliance/ — models (manifest, valueless records), policy (3 purposes), roles (role = purposes ∩ "
            "interop artefacts; authorise()), 7 rules, checkers, benchmark (compliance × cost), purpose_matrix, "
            "pseudonymise (HMAC tokens), handling (real-data gate).",
            "extraction/ — HISDataSource interface; adapters mock / portal (Playwright) / dataset (pandas, column "
            "map); techniques compliant / morality / unconstrained; metering; tier2 browser + navigation discovery.",
            "interop/ — HL7 v2 (ADT, ORM, ORU, DFT) and FHIR R4 (10 resources incl. AuditEvent) shapers; normalise + "
            "export audit. agent/ — 13-function registry, session state machine, grounded guidance. "
            "tools/mock_portal — the Flask fixture built as a system we do not control.",
        ]),
        ("Algorithms implemented:", [
            "Rule scoring: each principle → 0–1 with findings; weighted aggregate. Excess ratio = distinct fields "
            "pulled ÷ fields the purpose requires; coverage = needed fields obtained ÷ needed (micro-averaged).",
            "Layer inference: argmax over layers of catalogue-explained field names, with confidence — applied "
            "identically to a scraped module and an exported file. Role gate: lawful purpose → necessity → access "
            "control, first failure names its rule. Pseudonymisation: HMAC-SHA256 keyed per export; audit = search "
            "of emitted artefacts for raw identifier values.",
        ]),
    ], styles, heading_size=15, bullet_size=12)
    add_text(s[7], 0.7, 5.35, 11.9, 1.5, [
        "def authorise(role, purpose, artefacts):                       # compliance/roles.py",
        "    if purpose not in role_policy(role).purposes:  return deny(\"PL-01\")   # lawful purpose for this role?",
        "    if categories(artefacts) - policy_for(purpose).allowed_categories:  return deny(\"DM-01\")   # necessary?",
        "    if artefacts - role_policy(role).artefacts:    return deny(\"SS-01\")   # does the role handle these?",
        "    return permit()",
    ], size=10.5, font="Consolas", color=NAVY)

    # ---- slide 8 (index 8): Results & Analysis (75%) — the benchmark ----
    res = s[8]
    add_text(res, 0.7, 1.35, 11.9, 0.95, [
        "Three techniques, three extraction tasks, the same login-gated portal scraped by a real browser "
        "(30 records per module); every run scored on the identical seven rules; cost measured as real page loads. "
        "The techniques differ only in how they treat personal data.",
    ], size=12.5)
    add_table(res, 0.6, 2.4, 12.13, 2.55, [
        ["Technique", "Compliance", "Cost (excess · coverage · pages)", "Behaviour"],
        ["compliance-aware (ours)", "1.000  ·  7 / 7 rules", "1.00 · 1.00 · ~100",
         "Pulls what the purpose makes necessary; full manifest; identifiers pseudonymised on export."],
        ["morality (privacy by instinct)", "0.484  ·  2 / 7 rules", "0.85 · 0.85 · ~100",
         "Refuses what feels private (names, contact, money) whatever the purpose; takes MRN and DOB freely; "
         "consent assumed, no notice, no retention."],
        ["unconstrained (baseline)", "0.135  ·  0 / 7 rules", "7.15 · 1.00 · ~480",
         "Every field of every module; no purpose, no manifest, TLS only."],
    ], [2.9, 2.1, 2.6, 4.53], body_size=11.5)
    add_text(res, 0.7, 5.15, 11.9, 1.7, [
        "Reading the table. The baseline loads about five times the pages for the same coverage; its surplus is "
        "exactly the overreach DM-01 penalises, so compliance and cost move together rather than trading off.",
        "The morality model is the cheapest — and the cheapness is its failure: coverage 0.85 because it refused a "
        "name and a phone number an appointment reminder lawfully needs under the registration purpose. Privacy by "
        "instinct fails in both directions; only a purpose-bound technique gets both right. Per-rule columns "
        "(DM, LB, SL, SS, PL, NT, AC) are in docs/benchmark_results/benchmark-portal.md.",
    ], size=12)

    # ---- slide 9 (index 9): Results (contd.) — purpose matrix + export audit ----
    res2 = s[9]
    add_text(res2, 0.7, 1.35, 11.9, 0.95, [
        "The same extraction judged under every purpose — records, manifest and rules identical; only what the data "
        "was for changes. And the export audited, not trusted: the manifest claims pseudonymisation; we searched what "
        "actually left for the raw identifiers.",
    ], size=12.5)
    add_table(res2, 0.6, 2.4, 12.13, 1.5, [
        ["Care pull (MRN, DOB, sex, diagnosis, medication, allergy)", "under care_coordination",
         "under billing_settlement", "under patient_registration"],
        ["compliance score · rules passed", "1.000  ·  7 / 7", "0.833  ·  5 / 7", "0.881  ·  5 / 7"],
        ["why", "lawful for this purpose", "out of scope: clinical, quasi-identifier; notice does not cover it",
         "out of scope: clinical; notice does not cover it"],
    ], [4.6, 2.2, 2.9, 2.43], body_size=11)
    add_table(res2, 0.6, 4.2, 12.13, 1.3, [
        ["Export audit (HL7 v2 + FHIR)", "Pseudonymisation", "Raw identifiers found in the export"],
        ["compliance-aware (ours)", "declared → applied (HMAC tokens, PSN-…)", "0 of 120  ·  180 artefacts checked"],
        ["unconstrained (baseline)", "not declared → raw", "120 of 120  ·  510 artefacts checked"],
    ], [4.6, 3.6, 3.93], body_size=11)
    add_text(res2, 0.7, 5.7, 11.9, 1.2, [
        "Care may see clinical data and not billing data; billing may see billing data and not clinical data. Neither "
        "purpose is stricter — \"out of scope\" means not necessary for this purpose. Tokens are keyed hashes: stable "
        "within one export, unlinkable across exports, not reversible.",
    ], size=11.5)

    # ---- slide 9b: Results (contd.) — discovery & the assistant ----
    res3 = duplicate_slide(prs, 9)
    move_slide(prs, res3, 10)
    for sh in list(res3.shapes):
        if sh.name not in ("Text 0", "Text 1", "Image 0"):
            sh._element.getparent().remove(sh._element)
    rewrite_plain(shape_named(res3, "Text 1"), ["Results & Analysis (contd.) — Discovery & Assistant"])
    add_text(res3, 0.7, 1.35, 11.9, 1.15, [
        "The scraper is never told the portal's layout. It crawls from the home page and infers each module's HIS "
        "layer from the field names it finds — the URL says \"registration\", the scraper concludes patient "
        "administration. With display labels instead of field names it cannot classify the module; with a label→field "
        "map it is back at 100% and nothing downstream changes. The same inference classifies an exported spreadsheet.",
    ], size=12)
    add_table(res3, 0.6, 2.6, 12.13, 1.9, [
        ["Module (as the portal names it)", "Path", "Pages", "Inferred HIS layer", "Confidence"],
        ["Patient Registration", "/m/registration/", "2", "patient_administration", "100%"],
        ["Clinical Records", "/m/clinical/", "2", "clinical_ehr", "100%"],
        ["Departmental Orders", "/m/departments/", "2", "ancillary_departmental", "100%"],
        ["Billing & Accounts", "/m/billing/", "2", "administrative_financial", "100%"],
        ["Audit Log", "/m/integration/", "2", "infrastructure_integration", "100%"],
    ], [3.4, 2.2, 1.0, 3.6, 1.93], body_size=11)
    add_text(res3, 0.7, 4.7, 11.9, 2.2, [
        "reception > what is the patient's diagnosis",
        "assistant : I can't walk you through how to look up a patient's diagnosis as reception.",
        "            reception has no lawful purpose to act under 'care_coordination'; its purposes are "
        "billing_settlement, patient_registration.   [PL-01 — DPDP Act 2023 - purpose limitation]",
        "            This is something nurse can do; please hand it to them.        (declined before asking for any detail)",
        "The refusal comes from the same policy table that scored the benchmark. A nurse asking the same question is "
        "walked through it, each step stamped with the page the crawler found: [clinical_ehr / Condition / /m/clinical/].",
    ], size=11)

    # ---- Challenges & Remaining Work (index 11 after two insertions) ----
    chal = s[11]
    assert shape_named(chal, "Text 1").text_frame.text.startswith("Challenges")
    rewrite_body(shape_named(chal, "Text 2"), [
        ("Challenges faced and solutions:", [
            "No live HIS access — built a login-gated mock portal as a system we do not control (form login, session "
            "cookie, paginated HTML, robots.txt), so the browser layer is real and transfers as selectors + aliases.",
            "Measuring cost honestly — wall-clock is hardware-dependent, so deterministic metrics lead (fields, page "
            "loads, excess ratio) and coverage guards against pulling nothing.",
            "Trusting the manifest — pseudonymisation is now applied at export and audited against the emitted "
            "artefacts rather than taken from the declaration. Real data handling — the PLAN §4 checklist is enforced "
            "in code: a non-synthetic export is refused without provenance, de-identification statement and ignore rule.",
        ]),
        ("Remaining work (25%):", [
            "Project report and manuscript (compliance chapters need no real data; section mapping drafted, to be "
            "verified against the Gazette text). Real hospital dataset → one column map, then the same pipeline; "
            "results reported beside the synthetic ones. Three further literature references to reach fifteen.",
        ]),
        ("Timeline for completion by Review-III (28.10.2026):", [
            "Weeks 1–2: report chapters 3–4 (framework, techniques and cost) and 7 on synthetic data. Weeks 2–3: "
            "chapters 5–6, appendices; real-data integration the day the export lands. Week 4: manuscript "
            "compression, final results tables, rehearsal.",
        ]),
    ], styles, heading_size=15, bullet_size=12.5)

    # ---- References (index 12) ----
    refs = s[12]
    rewrite_plain(shape_named(refs, "Text 2"), REFERENCES, size=10.5)
    rewrite_plain(shape_named(refs, "Text 3"), [
        "IEEE format. [1]–[12] are cited on the literature slides; [13] on the problem, methodology and results slides."
    ])

    renumber(prs)
    prs.save(TARGET)
    return TARGET


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")
    print("Slide 1 is the template's instruction slide: replace it with the guide-signed Review-II scan.")
    print("Literature review has 12 rows; the template requires a minimum of 15 -- three references still to add.")
