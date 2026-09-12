"""Tests for the mock HIS portal, through Flask's test client (no browser)."""

from __future__ import annotations

import pytest

from extraction.adapters.mock_his import MockHISDataSource
from interop.layers import HISLayer
from tools.mock_portal import LIST_COLUMNS, MODULE_SLUGS, create_app

RECORDS, PAGE = 60, 25


@pytest.fixture()
def client():
    app = create_app(
        MockHISDataSource(records_per_layer=RECORDS, seed=7),
        users={"frontdesk": "letmein"},
        page_size=PAGE,
        secret_key="test",
    )
    app.config["TESTING"] = True
    return app.test_client()


def _login(client, username="frontdesk", password="letmein"):
    page = client.get("/login")
    token = page.data.decode().split('name="_token" value="')[1].split('"')[0]
    return client.post("/login", data={"_token": token, "username": username, "password": password})


# --- access control ----------------------------------------------------------

def test_everything_redirects_to_login_when_signed_out(client):
    for path in ("/", "/m/registration/", "/m/registration/record/0"):
        response = client.get(path)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_login_requires_the_form_token(client):
    response = client.post("/login", data={"username": "frontdesk", "password": "letmein"})
    assert response.status_code == 401


def test_wrong_password_is_rejected(client):
    assert _login(client, password="nope").status_code == 401
    assert client.get("/").status_code == 302


def test_login_then_home_then_logout(client):
    assert _login(client).status_code == 302
    home = client.get("/")
    assert home.status_code == 200
    assert b"Patient Registration" in home.data
    client.get("/logout")
    assert client.get("/").status_code == 302


def test_robots_disallows_everything(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert b"Disallow: /" in response.data


# --- module pages ------------------------------------------------------------

def test_home_lists_one_module_per_populated_layer(client):
    _login(client)
    html = client.get("/").data.decode()
    for layer in (HISLayer.PATIENT_ADMINISTRATION, HISLayer.CLINICAL_EHR,
                  HISLayer.ANCILLARY_DEPARTMENTAL, HISLayer.ADMINISTRATIVE_FINANCIAL):
        assert f"/m/{MODULE_SLUGS[layer]}/" in html
    assert "/m/integration/" not in html      # no records there; not a module


def test_list_page_shows_only_list_columns_and_paginates(client):
    _login(client)
    html = client.get("/m/registration/").data.decode()
    for column in LIST_COLUMNS[HISLayer.PATIENT_ADMINISTRATION]:
        assert f"<th>{column}</th>" in html
    assert "<th>phone</th>" not in html          # detail-only field
    assert "page 1 of 3" in html                  # 60 records / 25 per page
    assert html.count('">Open</a>') == PAGE


def test_last_page_has_the_remainder(client):
    _login(client)
    html = client.get("/m/registration/?page=3").data.decode()
    assert html.count('">Open</a>') == RECORDS - 2 * PAGE
    assert "Next &raquo;" not in html


def test_out_of_range_page_is_clamped_not_an_error(client):
    _login(client)
    assert client.get("/m/registration/?page=99").status_code == 200
    assert client.get("/m/registration/?page=0").status_code == 200


def test_detail_page_shows_fields_the_list_does_not(client):
    _login(client)
    html = client.get("/m/registration/record/0").data.decode()
    assert "<th>phone</th>" in html
    assert "<th>street_address</th>" in html
    assert "<th>date_of_birth</th>" in html


def test_detail_out_of_range_is_404(client):
    _login(client)
    assert client.get("/m/registration/record/999").status_code == 404
    assert client.get("/m/nonsense/").status_code == 404


def test_search_filters_the_list(client):
    _login(client)
    # Every synthetic ward is one of four values; searching for one narrows the list.
    html = client.get("/m/registration/?q=ICU").data.decode()
    assert 'matching "ICU"' in html
    assert html.count('">Open</a>') < RECORDS
    assert html.count('">Open</a>') > 0


def test_portal_serves_whatever_source_it_is_given():
    # A different source is a different portal, with no code change: the point
    # of building on the adapter boundary.
    small = create_app(MockHISDataSource(records_per_layer=3, seed=1), secret_key="t").test_client()
    _login(small)
    html = small.get("/m/billing/").data.decode()
    assert "3 records" in html
    assert html.count('">Open</a>') == 3
