"""Tier 2 against the mock portal: a real browser, over real HTTP.

One browser session per module (they are slow to start), shared across tests via
the ``scraper`` fixture. The suite asserts the things the project claims: the
adapter earns its data like a stranger would, the map is discovered rather than
given, the layer is inferred from content, and the techniques written against the
in-memory source run unchanged.
"""

from __future__ import annotations

import pytest

from compliance.benchmark import run_benchmark
from compliance.models import Purpose
from data_synthetic.catalogue import FIELD_CATALOGUE
from extraction.adapters.portal_his import PortalHISDataSource
from extraction.metering import MeteredSource
from extraction.technique import ExtractionTask, LayerFields
from extraction.techniques import DEFAULT_TECHNIQUES
from extraction.techniques.compliant import CompliantExtractionTechnique
from extraction.tier2 import LoginFailed, PortalBrowser, discover, infer_layer
from interop.layers import HISLayer

pytestmark = pytest.mark.usefixtures("browser_available")


@pytest.fixture(scope="module")
def scraper(portal):
    source = PortalHISDataSource(portal.url, portal.username, portal.password)
    yield source
    source.close()


# --- login is real -----------------------------------------------------------

def test_wrong_password_is_refused_by_the_portal(portal):
    with PortalBrowser(portal.url, portal.username, "wrong") as browser:
        with pytest.raises(LoginFailed):
            browser.login()


# --- discovery ---------------------------------------------------------------

def test_navigation_map_finds_every_populated_module(scraper, portal):
    nav = scraper.navigation
    assert len(nav.modules) == 4
    for module in nav.modules:
        assert module.columns, module.title
        assert module.detail_fields, module.title
        assert module.record_count == portal.records_per_layer
        assert module.page_count == -(-portal.records_per_layer // portal.page_size)


def test_layers_are_inferred_from_field_names_not_urls(scraper):
    nav = scraper.navigation
    inferred = {m.list_path: m.inferred_layer for m in nav.modules}
    # The URL says "registration"; the scraper concludes patient administration
    # because the fields are mrn / full_name / date_of_birth ...
    assert inferred["/m/registration/"] == HISLayer.PATIENT_ADMINISTRATION
    assert inferred["/m/clinical/"] == HISLayer.CLINICAL_EHR
    assert inferred["/m/departments/"] == HISLayer.ANCILLARY_DEPARTMENTAL
    assert inferred["/m/billing/"] == HISLayer.ADMINISTRATIVE_FINANCIAL
    assert all(m.layer_confidence == 1.0 for m in nav.modules)


def test_detail_only_fields_are_recorded(scraper):
    module = scraper.navigation.module_for(HISLayer.PATIENT_ADMINISTRATION)
    assert "phone" in module.detail_only()
    assert "mrn" not in module.detail_only()


def test_infer_layer_handles_unknown_and_empty():
    assert infer_layer([]) == (None, 0.0)
    assert infer_layer(["colour", "shape"]) == (None, 0.0)
    layer, confidence = infer_layer(["mrn", "full_name", "colour"])
    assert layer == HISLayer.PATIENT_ADMINISTRATION and confidence == round(2 / 3, 3)


def test_agent_pages_map_artefacts_to_discovered_modules(scraper):
    pages = scraper.navigation.agent_pages()
    assert pages["fhir:Patient"] == "/m/registration/"
    assert pages["fhir:Invoice"] == "/m/billing/"
    assert pages["fhir:Observation"] == "/m/departments/"


# --- fetching ----------------------------------------------------------------

def test_fetch_returns_every_record_across_pages(scraper, portal):
    rows = list(scraper.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"]))
    assert len(rows) == portal.records_per_layer
    assert all(set(r) == {"mrn", "sex"} for r in rows)
    assert all(r["mrn"].startswith("MRN") for r in rows)


def test_list_only_fields_do_not_open_detail_pages(scraper, portal):
    pages = -(-portal.records_per_layer // portal.page_size)
    before = scraper.page_loads
    list(scraper.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"]))
    assert scraper.page_loads - before == pages


def test_detail_fields_cost_one_page_per_record(scraper, portal):
    pages = -(-portal.records_per_layer // portal.page_size)
    before = scraper.page_loads
    rows = list(scraper.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "phone"]))
    assert scraper.page_loads - before == pages + portal.records_per_layer
    assert all("phone" in r for r in rows)


def test_fetch_without_fields_returns_every_field_of_the_layer(scraper):
    row = next(scraper.fetch(HISLayer.CLINICAL_EHR))
    assert set(row) == set(FIELD_CATALOGUE[HISLayer.CLINICAL_EHR])


def test_unknown_layer_yields_nothing(scraper):
    assert list(scraper.fetch(HISLayer.INFRASTRUCTURE_INTEGRATION)) == []


# --- the techniques run unchanged ---------------------------------------------

TASK = ExtractionTask(
    task_id="portal-summary",
    purpose=Purpose.CARE_COORDINATION,
    needed=[
        LayerFields(layer=HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "sex"]),
        LayerFields(layer=HISLayer.CLINICAL_EHR, fields=["primary_diagnosis"]),
    ],
)


def test_compliant_technique_runs_against_the_portal_unchanged(scraper, portal):
    output = CompliantExtractionTechnique().extract(scraper, TASK)
    assert len(output.records) == 2 * portal.records_per_layer
    assert output.run.purpose == Purpose.CARE_COORDINATION


def test_meter_reports_real_page_loads_for_a_portal_source(scraper, portal):
    metered = MeteredSource(scraper)
    CompliantExtractionTechnique().extract(metered, TASK)
    cost = metered.cost(TASK.field_refs(), elapsed_ms=0.0)
    pages = -(-portal.records_per_layer // portal.page_size)
    # Both needed layers are answered from list columns: pages only, no details.
    assert cost.page_loads == 2 * pages
    assert cost.excess_ratio == 1.0 and cost.coverage == 1.0


def test_benchmark_runs_all_three_techniques_against_the_portal(scraper):
    result = run_benchmark(DEFAULT_TECHNIQUES, [TASK], scraper, dataset_note="portal")
    scores = {s.short: s for s in result.scores}
    assert scores["compliance-aware"].mean_compliance_score == 1.0
    assert scores["unconstrained"].mean_compliance_score < 0.4
    # The baseline opens every module and every detail page; the cost shows it.
    assert scores["unconstrained"].cost.page_loads > scores["compliance-aware"].cost.page_loads
    assert scores["unconstrained"].cost.excess_ratio > 1.0
    assert "pages" in result.render_table()
