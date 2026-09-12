"""Tier 2 -- headless browser automation against a credentialed portal.

``browser``    a logged-in Playwright session: form login, table and detail parsing,
               "Next" following, a page-load counter.
``navigation`` crawl the portal from its home page, build a ``NavigationMap``, and
               infer each module's HIS layer from the field names it shows.

The adapter that puts these behind ``HISDataSource`` is
``extraction.adapters.portal_his.PortalHISDataSource``.
"""

from __future__ import annotations

from extraction.tier2.browser import LoginFailed, PortalBrowser, TablePage
from extraction.tier2.navigation import ModuleMap, NavigationMap, discover, infer_layer

__all__ = [
    "LoginFailed", "PortalBrowser", "TablePage",
    "ModuleMap", "NavigationMap", "discover", "infer_layer",
]
