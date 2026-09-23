"""Portal-backed ``HISDataSource``: Tier 2 scraping behind the same interface.

The three extraction techniques were written against ``MockHISDataSource``. They
run against this class **unchanged** -- that is the proof the adapter boundary was
designed correctly, and the demonstration that a new HIS is a new adapter, not a
downstream rewrite.

Cost is real here. ``fetch(layer, fields=...)`` reads from the list table when
every requested field is a list column, and opens a detail page per record only
when some requested field lives there. A technique that asks for more than it
needs therefore loads more pages, and ``page_loads`` says how many. The
compliance benchmark's metering picks that up as the honest cost column.

Field names are whatever the portal shows in its table headers. Our fixture shows
catalogue names by default and display labels when asked (``labels=``); a real
portal shows display labels. ``field_aliases`` maps label to catalogue field and
is applied as headers are read, so discovery, layer inference and fetching all see
catalogue names. That mapping is the one piece of portal-specific knowledge in the
chain, and it sits here, where it belongs.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from urllib.parse import quote

from extraction.base import HISDataSource
from extraction.tier2.browser import PortalBrowser
from extraction.tier2.navigation import NavigationMap, discover
from interop.layers import HISLayer


class PortalHISDataSource(HISDataSource):
    """Credentialed Tier 2 portal scraper behind the ``HISDataSource`` interface."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        navigation: NavigationMap | None = None,
        headless: bool = True,
        max_records: int | None = None,
        field_aliases: dict[str, str] | None = None,
    ) -> None:
        self._browser = PortalBrowser(
            base_url, username, password, headless=headless,
            field_aliases=dict(field_aliases or {}),
        )
        self._browser.open()
        self._browser.login()
        self.navigation = navigation or discover(self._browser)
        self.max_records = max_records

    # ---------------------------------------------------------------- source

    @property
    def page_loads(self) -> int:
        """Pages the browser has loaded so far -- the cost the meter reads."""

        return self._browser.page_loads

    @property
    def transport_secure(self) -> bool | None:
        """Observed, not declared: the scheme of the URL the browser was pointed at."""

        return self._browser.base_url.lower().startswith("https://")

    def layers(self) -> tuple[HISLayer, ...]:
        return self.navigation.layers()

    def fields(self, layer: HISLayer) -> list[str] | None:
        module = self.navigation.module_for(layer)
        return [] if module is None else list(module.all_fields())

    def fetch(
        self,
        layer: HISLayer,
        *,
        fields: list[str] | None = None,
        where: dict[str, Any] | None = None,
        **query: Any,
    ) -> Iterator[dict[str, Any]]:
        module = self.navigation.module_for(layer)
        if module is None:
            return

        wanted = list(fields) if fields is not None else module.all_fields()
        # Only open a record when something asked for is not in the list table.
        need_detail = any(name not in module.columns for name in wanted)

        # A scoped pull goes through the portal's search box, the way a person
        # would: one value, one (usually one-page) result, then an exact match
        # on the field so a substring hit on another column is not taken.
        where = dict(where or {})
        first_url = module.list_url
        if where:
            first_url = f"{module.list_url}{'&' if '?' in module.list_url else '?'}q={quote(str(next(iter(where.values()))))}"

        yielded = 0
        for table in self._browser.iter_table_pages(first_url):
            for row, link in zip(table.rows, table.row_links):
                if self.max_records is not None and yielded >= self.max_records:
                    return
                if where and any(str(row.get(k, "")) != str(v) for k, v in where.items() if k in row):
                    continue
                if need_detail and link:
                    self._browser.goto(link)
                    record = self._browser.read_detail()
                else:
                    record = row
                if where and any(str(record.get(k, "")) != str(v) for k, v in where.items()):
                    continue
                yield {name: record[name] for name in wanted if name in record}
                yielded += 1

    def close(self) -> None:
        self._browser.close()
