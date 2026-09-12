"""Shared fixtures.

``portal`` serves the mock HIS portal on a free local port for the duration of
the test module, in a background thread, so Tier 2 tests drive it with a real
browser over real HTTP. Small dataset and small pages: enough to paginate, not
enough to be slow.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from extraction.adapters.mock_his import MockHISDataSource
from tools.mock_portal.serve import BackgroundPortal

PORTAL_RECORDS = 7
PORTAL_PAGE = 3


@dataclass
class RunningPortal:
    url: str
    username: str
    password: str
    records_per_layer: int
    page_size: int


@pytest.fixture(scope="module")
def portal():
    source = MockHISDataSource(records_per_layer=PORTAL_RECORDS, seed=11)
    with BackgroundPortal(source, page_size=PORTAL_PAGE, secret_key="test") as running:
        yield RunningPortal(
            url=running.url,
            username=running.username,
            password=running.password,
            records_per_layer=PORTAL_RECORDS,
            page_size=PORTAL_PAGE,
        )


@pytest.fixture(scope="session")
def browser_available() -> bool:
    """Skip Tier 2 tests cleanly where the browser binaries are not installed."""

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        return True
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"chromium not available for Playwright: {exc}")
