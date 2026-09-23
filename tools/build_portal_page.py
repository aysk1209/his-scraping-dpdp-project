"""Build the interactive portal page: a real browser, a portal we do not control, every page it loaded.

    python tools/build_portal_page.py                 # ~1 min: the same run as run_pipeline.py stages 1-3

Serves the fixture portal (``tools/mock_portal``, 20 records per module, 10 per
page, TLS, robots.txt disallowing everything), lets the Tier 2 browser log in
and discover it, then runs the benchmark against it -- exactly what
``scripts/run_pipeline.py`` does -- while recording **every page the browser
loads**, and which technique on which task loaded it. The page shows:

    1  The portal     what the scraper holds (a username and a password) and what
                      it faces (a login form, TLS, robots.txt, HTML tables)
    2  Discovery      each module, the layer inferred from the field names it
                      found -- never from the URL -- and the evidence per field
    3  The crawl      every technique's page loads replayed on a map of the site:
                      ours goes through the search box, the baseline opens everything
    4  The score      the benchmark from the same run

The page loads are captured by wrapping ``PortalBrowser.goto`` and ``login`` for
the length of the build; no core code knows. Loads the harness makes outside the
meter (counting a patient's own records, the coverage ceiling) are labelled as
the harness's, not charged to a technique. The per-technique totals are checked
against the benchmark's own page-load counts before the page is written.

Nothing personal is on the page: a search is shown as a pseudonym, never the
record number typed into the box; the builder searches its output for every
identifier the portal serves.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from compliance.audit import AuditLog                                     # noqa: E402
from compliance.benchmark import run_benchmark                           # noqa: E402
from compliance.models import FieldCategory                              # noqa: E402
from compliance.pseudonymise import token_for                            # noqa: E402
from data_synthetic.catalogue import FIELD_CATALOGUE                     # noqa: E402
from extraction.adapters.mock_his import MockHISDataSource               # noqa: E402
from extraction.adapters.portal_his import PortalHISDataSource           # noqa: E402
from extraction.techniques import default_techniques                     # noqa: E402
from extraction.tier2.browser import PortalBrowser                       # noqa: E402
from tools.mock_portal.serve import BackgroundPortal                     # noqa: E402
from tools.page_kit import REVIEW_DIR, render, write                     # noqa: E402

TEMPLATE = ROOT / "tools" / "portal_page.html"
DEFAULT_OUT = REVIEW_DIR / "portal-run.html"
RECORDS, PAGE_SIZE, SEED = 20, 10, 42
_LIST = re.compile(r"^/m/([^/]+)/$")
_DETAIL = re.compile(r"^/m/([^/]+)/record/(\d+)$")


class PageLeak(RuntimeError):
    pass


class PageTrace:
    """Every page the browser loads, tagged with who was driving it."""

    def __init__(self) -> None:
        self.phase: tuple[str, str | None] = ("discover", None)
        self.visits: list[dict] = []
        self._saved = None

    def record(self, browser: PortalBrowser, url: str | None, kind: str | None = None) -> None:
        who, task = self.phase
        visit = {"who": who, "task": task}
        if kind:
            visit.update(kind=kind)
        else:
            parsed = urlparse(urljoin(browser.base_url, url or ""))
            path, query = parsed.path, parse_qs(parsed.query)
            if (m := _DETAIL.match(path)):
                visit.update(kind="detail", module=m.group(1), n=int(m.group(2)))
            elif (m := _LIST.match(path)):
                if query.get("q"):
                    # The value typed into the search box is a record number: shown as a pseudonym.
                    visit.update(kind="search", module=m.group(1), q=token_for(query["q"][0], key="portal-page"),
                                 n=int(query.get("page", ["1"])[0]))
                else:
                    visit.update(kind="list", module=m.group(1), n=int(query.get("page", ["1"])[0]))
            elif path == "/":
                visit.update(kind="home")
            elif path.startswith("/login"):
                visit.update(kind="login")
            else:
                visit.update(kind="other", path=path)
        self.visits.append(visit)

    def install(self) -> None:
        trace, goto, login = self, PortalBrowser.goto, PortalBrowser.login
        self._saved = (goto, login)

        def traced_goto(browser, url):
            trace.record(browser, url)
            return goto(browser, url)

        def traced_login(browser, login_path="/login"):
            result = login(browser, login_path)          # its GET goes through traced_goto
            trace.record(browser, None, kind="login-submit")
            return result

        PortalBrowser.goto, PortalBrowser.login = traced_goto, traced_login

    def remove(self) -> None:
        if self._saved:
            PortalBrowser.goto, PortalBrowser.login = self._saved
            self._saved = None


def _label(technique, trace: PageTrace) -> None:
    """Tag every page load made inside this technique's extract with its name and task."""

    original = technique.extract

    def extract(source, task):
        trace.phase = (technique.name, task.task_id)
        try:
            return original(source, task)
        finally:
            trace.phase = ("harness", None)

    technique.extract = extract


def _evidence(field: str) -> list[str]:
    return [layer.value for layer, fields in FIELD_CATALOGUE.items() if field in fields]


def build(out: Path = DEFAULT_OUT, *, audit_log: AuditLog | None = None,
          records: int = RECORDS, page_size: int = PAGE_SIZE) -> dict:
    from run_pipeline import TASKS

    source = MockHISDataSource(records_per_layer=records, seed=SEED)
    trace = PageTrace()
    trace.install()
    try:
        with BackgroundPortal(source, page_size=page_size, latency_ms=0) as portal:
            robots = portal.app.test_client().get("/robots.txt").get_data(as_text=True)
            scraper = PortalHISDataSource(portal.url, portal.username, portal.password)
            discovery_loads = len(trace.visits)
            techniques = default_techniques(TASKS, scraper)
            for t in techniques:
                _label(t, trace)
            trace.phase = ("harness", None)
            result = run_benchmark(techniques, TASKS, scraper, dataset_note=f"portal, {records} records/module",
                                   audit=audit_log or AuditLog())
            nav = scraper.navigation
            scraper.close()
            username = portal.username
    finally:
        trace.remove()

    # The benchmark's own page-load count per technique must equal what the trace saw.
    for s in result.scores:
        seen = sum(1 for v in trace.visits if v["who"] == s.technique)
        if s.cost.page_loads is not None and seen != s.cost.page_loads:
            raise RuntimeError(f"trace saw {seen} page loads for {s.technique}; the meter counted {s.cost.page_loads}")

    modules = []
    for m in nav.modules:
        slug = m.list_path.strip("/").split("/")[-1]
        modules.append({
            "slug": slug, "title": m.title, "path": m.list_path, "pages": m.page_count, "records": m.record_count,
            "layer": m.inferred_layer.value if m.inferred_layer else None, "confidence": m.layer_confidence,
            "columns": m.columns, "detail_only": m.detail_only(),
            "evidence": {f: _evidence(f) for f in m.all_fields()},
        })

    def kind(s):
        return "ours" if s.short == "compliance-aware" else ("baseline" if s.short == "unconstrained" else "agent")

    techniques_view = [{
        "name": s.technique, "kind": kind(s), "briefing": s.briefing, "score": s.mean_compliance_score,
        "pages": s.cost.page_loads, "coverage": s.cost.coverage, "excess": s.cost.excess_ratio,
        "record_excess": s.cost.record_excess, "records": s.cost.records, "traps": s.traps_note(),
        "per_task": s.per_task, "rules": s.per_rule_mean,
    } for s in result.scores]
    headline = [s.technique for s, _ in result.by_model()]

    data = {
        "meta": {"records": records, "page_size": page_size, "seed": SEED, "generated": result.generated_at.date().isoformat(),
                 "tls": result.observed_transport, "account": username, "robots": robots.strip(),
                 "discovery_loads": discovery_loads, "elapsed_s": round((result.elapsed_ms or 0) / 1000, 1)},
        "modules": modules,
        "tasks": [{"id": t.task_id, "purpose": t.purpose.value, "description": t.description,
                   "single": t.single_subject, "trap": t.trap or ""} for t in TASKS],
        "techniques": techniques_view,
        "headline": headline,
        "visits": trace.visits,
        "rule_ids": result.rule_ids,
        "takeaway": result._takeaway(),
        "categories": {layer.value: {f: c.value for f, c in fields.items()} for layer, fields in FIELD_CATALOGUE.items()},
    }
    page = render(TEMPLATE, data, current="portal", out=out)

    identifiers = set()
    for layer, rows in source._data.items():
        for row in rows:
            for name, value in row.items():
                if FIELD_CATALOGUE[layer].get(name) in (FieldCategory.DIRECT_IDENTIFIER, FieldCategory.CONTACT) \
                        and value and len(str(value)) >= 4:
                    identifiers.add(str(value))
    if any(v in page for v in identifiers):
        raise PageLeak("a portal identifier would be on the page -- not written")
    write(out, page)
    return data


def main() -> int:
    data = build()
    loads = {t["name"]: t["pages"] for t in data["techniques"]}
    print(f"  wrote {DEFAULT_OUT}")
    print(f"  {len(data['visits'])} page loads traced ({data['meta']['discovery_loads']} discovery); "
          + "; ".join(f"{k}: {v}" for k, v in loads.items()))
    print("  page audit: no portal identifier on the page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
