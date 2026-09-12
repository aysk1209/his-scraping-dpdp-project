"""A portal that shows display labels, and the adapter's label-to-field mapping.

This is the real-portal case rehearsed against the fixture: headers read
"Patient ID", not ``mrn``. Without a mapping, the crawler cannot classify the
module and the adapter cannot serve it; with one, everything downstream is
unchanged. The mapping is the entire integration.
"""

from __future__ import annotations

import pytest

from extraction.adapters.mock_his import MockHISDataSource
from extraction.adapters.portal_his import PortalHISDataSource
from interop.layers import HISLayer
from tools.mock_portal.serve import BackgroundPortal

pytestmark = pytest.mark.usefixtures("browser_available")

LABELS = {
    "mrn": "Patient ID", "full_name": "Patient Name", "sex": "Gender",
    "date_of_birth": "DOB", "phone": "Contact No.", "admission_ward": "Ward",
}
ALIASES = {label: field for field, label in LABELS.items()}


@pytest.fixture(scope="module")
def labelled_portal():
    source = MockHISDataSource(records_per_layer=4, seed=3)
    with BackgroundPortal(source, page_size=2, secret_key="t", labels=LABELS) as running:
        yield running


def test_without_aliases_the_labelled_module_is_not_understood(labelled_portal):
    src = PortalHISDataSource(labelled_portal.url, labelled_portal.username, labelled_portal.password)
    try:
        module = next(m for m in src.navigation.modules if m.list_path == "/m/registration/")
        # Six of ten headers are display labels the catalogue does not know.
        assert module.layer_confidence < 0.5
        assert "Patient ID" in module.columns
    finally:
        src.close()


def test_with_aliases_the_same_portal_is_fully_understood(labelled_portal):
    src = PortalHISDataSource(
        labelled_portal.url, labelled_portal.username, labelled_portal.password,
        field_aliases=ALIASES,
    )
    try:
        module = src.navigation.module_for(HISLayer.PATIENT_ADMINISTRATION)
        assert module is not None and module.layer_confidence == 1.0
        assert "mrn" in module.columns and "Patient ID" not in module.columns
        rows = list(src.fetch(HISLayer.PATIENT_ADMINISTRATION, fields=["mrn", "phone"]))
        assert len(rows) == 4
        assert all(set(r) == {"mrn", "phone"} for r in rows)      # catalogue names, detail-only field resolved
    finally:
        src.close()


def test_alias_matching_ignores_case_and_spacing():
    from extraction.tier2.browser import PortalBrowser
    browser = PortalBrowser("http://x", "u", "p", field_aliases={"Patient  ID": "mrn"})
    assert browser.field_name("patient id") == "mrn"
    assert browser.field_name("PATIENT ID ") == "mrn"
    assert browser.field_name("Something Else") == "Something Else"
