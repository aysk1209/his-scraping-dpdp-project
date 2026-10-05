"""A vendor release splits billing in two; the scraper reads across the split.

Layout v2 serves the administrative-financial layer as two modules, "Accounts"
(invoice and amount) and "Insurance & Payers" (payer and policy number). The
crawl files both under the layer; a request for fields from both is read from
each and joined on the patient key, and every page it costs is counted.
"""

from __future__ import annotations

import pytest

from extraction.adapters.mock_his import MockHISDataSource
from extraction.adapters.portal_his import PortalHISDataSource
from interop.layers import HISLayer
from tools.mock_portal.layouts import V2_FIELD_ALIASES
from tools.mock_portal.serve import BackgroundPortal

pytestmark = pytest.mark.usefixtures("browser_available")

FIN = HISLayer.ADMINISTRATIVE_FINANCIAL
ALIASES = {**V2_FIELD_ALIASES, "Unit": "admission_ward"}


@pytest.fixture(scope="module")
def sources():
    data = MockHISDataSource(records_per_layer=5, seed=11)
    with BackgroundPortal(data, page_size=3, secret_key="t", layout="v2") as portal:
        scraper = PortalHISDataSource(portal.url, portal.username, portal.password, field_aliases=ALIASES)
        yield data, scraper
        scraper.close()


def test_the_crawl_files_both_halves_under_one_layer(sources):
    _, scraper = sources
    titles = [m.title for m in scraper.navigation.modules_for(FIN)]
    assert sorted(titles) == ["Accounts", "Insurance & Payers"]
    assert scraper.layers().count(FIN) == 1
    assert {"invoice_id", "payer_name", "insurance_policy_no"} <= set(scraper.fields(FIN))


def test_fields_from_both_halves_join_into_the_same_records_as_the_source(sources):
    data, scraper = sources
    wanted = ["mrn", "invoice_id", "billed_amount", "payer_name", "insurance_policy_no"]
    before = scraper.page_loads
    got = list(scraper.fetch(FIN, fields=wanted))
    truth = [{k: str(v) for k, v in r.items()} for r in data.fetch(FIN, fields=wanted)]
    assert got == truth
    assert scraper.page_loads > before


def test_a_request_inside_one_half_reads_only_that_half(sources):
    _, scraper = sources
    before = scraper.page_loads
    rows = list(scraper.fetch(FIN, fields=["mrn", "invoice_id"]))
    assert rows and all(set(r) == {"mrn", "invoice_id"} for r in rows)
    # Two list pages of five records, no record pages: one module was read.
    assert scraper.page_loads - before == 2


def test_a_scoped_pull_goes_through_both_search_boxes(sources):
    data, scraper = sources
    mrn = next(iter(data.fetch(FIN, fields=["mrn"])))["mrn"]
    rows = list(scraper.fetch(FIN, fields=["invoice_id", "payer_name"], where={"mrn": mrn}))
    assert len(rows) == 1 and set(rows[0]) == {"invoice_id", "payer_name"}
