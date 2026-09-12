"""Discover a portal's structure by crawling it, then work out what it holds.

The scraper is never told how the portal is laid out. From the home page it
follows the module links it finds; on each module it reads the table's column
names, the page count, and one detail record to learn the fields the list does
not show. That is the **navigation map**.

Then it infers, for each module, which HIS layer it is -- by matching the field
names it saw against the field catalogue and taking the layer with the most
overlap. The portal's URL says ``/m/registration/``; the scraper concludes
"patient administration" from the fact that the fields are ``mrn``,
``full_name``, ``date_of_birth``. Content, not labels. This is the answer to the
Review-1 panel's heterogeneity question expressed as code: point it at a portal
with different names and the map re-derives itself.

The map has two consumers. ``PortalHISDataSource`` uses it to know where a layer's
records live and which fields need a detail page. The staff-guidance agent uses
``agent_pages()`` to put a real page on each instruction step.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from compliance.roles import ARTEFACTS
from data_synthetic.catalogue import infer_layer
from extraction.tier2.browser import PortalBrowser
from interop.layers import HISLayer

_REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = _REPO_ROOT / "docs" / "benchmark_results"


class ModuleMap(BaseModel):
    """What the crawler learned about one portal module."""

    title: str
    list_url: str                                  # absolute
    list_path: str                                 # path only, for reports and the agent
    columns: list[str]                             # fields visible in the list table
    detail_fields: list[str]                       # fields visible on a record page
    page_count: int | None = None
    record_count: int | None = None
    inferred_layer: HISLayer | None = None
    layer_confidence: float = 0.0                  # share of seen fields the layer's catalogue explains

    def all_fields(self) -> list[str]:
        seen: list[str] = []
        for name in [*self.columns, *self.detail_fields]:
            if name and name not in seen:
                seen.append(name)
        return seen

    def detail_only(self) -> list[str]:
        return [f for f in self.detail_fields if f not in self.columns]


class NavigationMap(BaseModel):
    base_url: str
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    login_path: str = "/login"
    page_loads: int = 0                             # what discovery itself cost
    modules: list[ModuleMap]

    def module_for(self, layer: HISLayer) -> ModuleMap | None:
        best = None
        for module in self.modules:
            if module.inferred_layer == layer and (
                best is None or module.layer_confidence > best.layer_confidence
            ):
                best = module
        return best

    def layers(self) -> tuple[HISLayer, ...]:
        return tuple(m.inferred_layer for m in self.modules if m.inferred_layer is not None)

    def agent_pages(self) -> dict[str, str]:
        """Artefact key -> portal page, for ``agent.Session(navigation=...)``.

        Every artefact lives on a HIS layer; if the crawler found a module for
        that layer, the artefact's steps happen on that module's page.
        """

        by_layer = {m.inferred_layer: m.list_path for m in self.modules if m.inferred_layer}
        return {key: by_layer[a.layer] for key, a in ARTEFACTS.items() if a.layer in by_layer}

    def render_table(self) -> str:
        lines = [
            f"Navigation map -- {self.base_url}  (discovered in {self.page_loads} page loads)",
            "",
            f"  {'module':<22} {'path':<20} {'pages':>5} {'records':>8}  inferred layer",
            "  " + "-" * 82,
        ]
        for m in self.modules:
            layer = f"{m.inferred_layer.value} ({m.layer_confidence:.0%})" if m.inferred_layer else "?"
            lines.append(
                f"  {m.title:<22} {m.list_path:<20} {str(m.page_count or '?'):>5} "
                f"{str(m.record_count or '?'):>8}  {layer}"
            )
        lines.append("")
        for m in self.modules:
            lines.append(f"  {m.title}")
            lines.append(f"    in list      : {', '.join(m.columns)}")
            lines.append(f"    detail only  : {', '.join(m.detail_only()) or '-'}")
        return "\n".join(lines)

    def to_json_file(self, directory: Path | None = None) -> Path:
        directory = directory or ARTIFACT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "navigation-map.json"
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path


def discover(browser: PortalBrowser, *, home_path: str = "/") -> NavigationMap:
    """Crawl from the home page and build the map. The browser must be logged in."""

    start_loads = browser.page_loads
    browser.goto(home_path)
    home_url = browser.page.url

    # Module links are the ones on the home page that lead somewhere other than
    # home, sign-out, or the login page. Deduplicated in order of appearance.
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()
    for text, href in browser.links("main"):
        path = urlparse(href).path
        if href == home_url or path in ("/", "/login", "/logout") or href in seen:
            continue
        seen.add(href)
        candidates.append((text or path, href))

    modules: list[ModuleMap] = []
    for title, href in candidates:
        browser.goto(href)
        table = browser.read_table()
        if not table.columns:
            continue                                # not a list module; skip it

        detail_fields: list[str] = []
        first_link = next((l for l in table.row_links if l), None)
        if first_link:
            browser.goto(first_link)
            detail_fields = list(browser.read_detail().keys())

        fields = list(dict.fromkeys([*table.columns, *detail_fields]))
        layer, confidence = infer_layer(fields)
        modules.append(
            ModuleMap(
                title=title,
                list_url=href,
                list_path=urlparse(href).path,
                columns=table.columns,
                detail_fields=detail_fields,
                page_count=table.page_count,
                record_count=table.record_count,
                inferred_layer=layer,
                layer_confidence=confidence,
            )
        )

    return NavigationMap(
        base_url=browser.base_url,
        page_loads=browser.page_loads - start_loads,
        modules=modules,
    )
