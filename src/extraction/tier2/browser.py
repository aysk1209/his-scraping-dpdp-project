"""Tier 2 browser machinery: a real browser against a portal we do not control.

Everything here is what a scraper has to do when it holds a username and a
password and nothing else. Log in through the form (the browser carries the
hidden token and the cookie, as a browser does). Read tables as a reader would --
header cells for names, body cells for values, the link in the last column to open
a record. Turn pages by following the "Next" link until there is none. Count every
page the browser loads, because that is the cost.

Nothing here knows the portal is ours. It uses generic selectors -- ``table``,
``thead th``, ``tbody tr``, ``a`` -- and text, not ids or data attributes, so it
transfers to a real portal as a change of selectors and credentials rather than of
approach.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

_PAGE_OF = re.compile(r"page\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE)
_RECORDS = re.compile(r"(\d+)\s+records?\b", re.IGNORECASE)


class LoginFailed(RuntimeError):
    pass


@dataclass
class TablePage:
    """One rendered list page: column names, rows, and the link that opens each row."""

    columns: list[str]
    rows: list[dict[str, str]]
    row_links: list[str | None]
    page_number: int | None = None
    page_count: int | None = None
    record_count: int | None = None
    next_url: str | None = None


@dataclass
class PortalBrowser:
    """A logged-in browser session against one portal. Use as a context manager."""

    base_url: str
    username: str
    password: str
    headless: bool = True
    # Display label -> catalogue field. A real portal shows "Patient ID", not
    # ``mrn``; this is where that portal-specific knowledge lives. Matching is
    # case- and whitespace-insensitive; unmapped headers pass through unchanged.
    field_aliases: dict[str, str] = field(default_factory=dict)
    page_loads: int = 0
    _pw: Playwright | None = field(default=None, repr=False)
    _browser: Browser | None = field(default=None, repr=False)
    _context: BrowserContext | None = field(default=None, repr=False)
    _page: Page | None = field(default=None, repr=False)

    # ---------------------------------------------------------------- lifecycle

    def __enter__(self) -> "PortalBrowser":
        self.open()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def open(self) -> None:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context()
        self._page = self._context.new_page()

    def close(self) -> None:
        for closer in (self._context, self._browser):
            if closer is not None:
                closer.close()
        if self._pw is not None:
            self._pw.stop()
        self._pw = self._browser = self._context = self._page = None

    @property
    def page(self) -> Page:
        assert self._page is not None, "PortalBrowser is not open"
        return self._page

    def field_name(self, header: str) -> str:
        """Map a header as displayed to the catalogue field it means."""

        key = " ".join(header.split()).lower()
        for label, name in self.field_aliases.items():
            if " ".join(label.split()).lower() == key:
                return name
        return header

    # --------------------------------------------------------------- navigation

    def goto(self, url: str) -> Page:
        """Load a URL (absolute or portal-relative) and count it."""

        self.page.goto(urljoin(self.base_url, url), wait_until="domcontentloaded")
        self.page_loads += 1
        return self.page

    def login(self, login_path: str = "/login") -> None:
        """Submit the login form the way a person would; the browser carries the token."""

        self.goto(login_path)
        page = self.page
        page.fill("input[name='username']", self.username)
        page.fill("input[name='password']", self.password)
        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_load_state("domcontentloaded")
        self.page_loads += 1
        if "/login" in page.url or page.locator("input[name='password']").count():
            raise LoginFailed(f"login as {self.username!r} was rejected by {self.base_url}")

    def links(self, scope: str = "main") -> list[tuple[str, str]]:
        """(text, absolute href) for every link inside ``scope`` on the current page."""

        out: list[tuple[str, str]] = []
        for anchor in self.page.locator(f"{scope} a[href]").all():
            href = anchor.get_attribute("href") or ""
            out.append((anchor.inner_text().strip(), urljoin(self.page.url, href)))
        return out

    # ------------------------------------------------------------------ parsing

    def read_table(self) -> TablePage:
        """Parse the first table on the current page as a list of records.

        The last header cell is treated as the actions column when it is blank,
        and the first link in that cell is the record's detail link.
        """

        page = self.page
        headers = [h.inner_text().strip() for h in page.locator("table thead th").all()]
        has_actions = bool(headers) and headers[-1] == ""
        columns = [self.field_name(h) for h in (headers[:-1] if has_actions else headers)]

        rows: list[dict[str, str]] = []
        row_links: list[str | None] = []
        for tr in page.locator("table tbody tr").all():
            cells = tr.locator("td").all()
            values = [c.inner_text().strip() for c in cells]
            rows.append(dict(zip(columns, values)))
            link = None
            if has_actions and cells:
                anchor = cells[-1].locator("a[href]")
                if anchor.count():
                    link = urljoin(page.url, anchor.first.get_attribute("href") or "")
            row_links.append(link)

        text = page.locator("main").inner_text()
        page_of = _PAGE_OF.search(text)
        records = _RECORDS.search(text)
        next_url = None
        for label, href in self.links():
            if label.lower().startswith("next"):
                next_url = href
                break

        return TablePage(
            columns=columns,
            rows=rows,
            row_links=row_links,
            page_number=int(page_of.group(1)) if page_of else None,
            page_count=int(page_of.group(2)) if page_of else None,
            record_count=int(records.group(1)) if records else None,
            next_url=next_url,
        )

    def read_detail(self) -> dict[str, str]:
        """Parse a detail page laid out as name / value rows."""

        record: dict[str, str] = {}
        for tr in self.page.locator("table tbody tr").all():
            name = tr.locator("th").first.inner_text().strip()
            value = tr.locator("td").first.inner_text().strip()
            if name:
                record[self.field_name(name)] = value
        return record

    def iter_table_pages(self, first_url: str, *, max_pages: int | None = None):
        """Yield every list page from ``first_url``, following "Next" until it stops."""

        url: str | None = first_url
        seen = 0
        while url and (max_pages is None or seen < max_pages):
            self.goto(url)
            table = self.read_table()
            seen += 1
            yield table
            url = table.next_url
