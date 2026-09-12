"""A rough, login-gated HIS portal for the Tier 2 browser layer to scrape.

This is a **test fixture**, not a product, and it is built on one rule: *assume
we do not control it.* The scraper holds a username and a password, and nothing
else. So the portal offers what a third-party system would offer and no more --

- a login form with a per-session token, a session cookie, a redirect to the
  login page for anything unauthenticated;
- server-rendered HTML tables, paginated, with a search box;
- a detail page per record that shows fields the list page does not;
- a `robots.txt` that disallows everything, as a credentialed portal would.

No JSON endpoint, no data attributes for the scraper's convenience, no stable
API. If the Tier 2 adapter can read this, it is because it does what it would
have to do against a real portal: submit the form, keep the cookie, follow the
links, turn the pages, parse the tables.

It serves whatever ``HISDataSource`` it is given, so the same portal shows
synthetic records today and the hospital dataset when that lands
(``DatasetHISDataSource``), with no change here. Records are read from the source
once at start-up and held in memory; with 20 000 rows that is a few megabytes and
makes pagination cheap.

    python -m tools.mock_portal --records 500 --seed 42 --port 8765

Deliberately rough: no CSS beyond the minimum, no JavaScript, a handful of pages.
It exists to exercise the browser layer and to make techniques cost different
amounts, not to imitate a hospital system.
"""

from __future__ import annotations

import secrets
import time
from functools import wraps
from typing import Any

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from extraction.base import HISDataSource
from interop.layers import LAYER_DESCRIPTIONS, HISLayer

# Columns shown on the list page, per layer. Everything else is only on the detail
# page -- which is what makes a coverage-optimised scraper open more pages than a
# minimising one, and so what gives the benchmark's ``fetches`` column something
# to measure. The choice is what a portal would plausibly show in a table, not a
# choice made for the benchmark's sake.
LIST_COLUMNS: dict[HISLayer, list[str]] = {
    HISLayer.PATIENT_ADMINISTRATION: ["mrn", "full_name", "sex", "admission_ward"],
    HISLayer.CLINICAL_EHR: ["encounter_datetime", "primary_diagnosis", "attending_clinician"],
    HISLayer.ANCILLARY_DEPARTMENTAL: ["order_id", "specimen_type", "imaging_modality"],
    HISLayer.ADMINISTRATIVE_FINANCIAL: ["invoice_id", "billed_amount", "payer_name"],
}

# A portal's module names, not our layer names -- the scraper should not get the
# five-layer vocabulary for free from the URL.
MODULE_SLUGS: dict[HISLayer, str] = {
    HISLayer.PATIENT_ADMINISTRATION: "registration",
    HISLayer.CLINICAL_EHR: "clinical",
    HISLayer.ANCILLARY_DEPARTMENTAL: "departments",
    HISLayer.ADMINISTRATIVE_FINANCIAL: "billing",
    HISLayer.INFRASTRUCTURE_INTEGRATION: "integration",
}
MODULE_TITLES: dict[HISLayer, str] = {
    HISLayer.PATIENT_ADMINISTRATION: "Patient Registration",
    HISLayer.CLINICAL_EHR: "Clinical Records",
    HISLayer.ANCILLARY_DEPARTMENTAL: "Departmental Orders",
    HISLayer.ADMINISTRATIVE_FINANCIAL: "Billing & Accounts",
    HISLayer.INFRASTRUCTURE_INTEGRATION: "Integration",
}
_SLUG_TO_LAYER = {slug: layer for layer, slug in MODULE_SLUGS.items()}

DEFAULT_USERS = {"frontdesk": "letmein"}


def create_app(
    source: HISDataSource,
    *,
    users: dict[str, str] | None = None,
    page_size: int = 25,
    latency_ms: int = 0,
    secret_key: str | None = None,
) -> Flask:
    """Build the portal over ``source``. Records are snapshotted at creation."""

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secret_key or secrets.token_hex(16),
        PAGE_SIZE=page_size,
        LATENCY_MS=latency_ms,
        USERS=dict(users or DEFAULT_USERS),
    )

    # Snapshot: one pass through the adapter, then in-memory pages.
    data: dict[HISLayer, list[dict[str, Any]]] = {
        layer: list(source.fetch(layer)) for layer in source.layers()
    }
    app.config["DATA"] = data
    app.config["MODULES"] = [layer for layer in data if data[layer]]

    # ------------------------------------------------------------- helpers --

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user"):
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def layer_or_404(slug: str) -> HISLayer:
        layer = _SLUG_TO_LAYER.get(slug)
        if layer is None or layer not in data:
            abort(404)
        return layer

    @app.before_request
    def _latency() -> None:
        # A real portal is not in-process. A little wall-clock per request keeps
        # the benchmark's timing column from being pure noise.
        if app.config["LATENCY_MS"]:
            time.sleep(app.config["LATENCY_MS"] / 1000)

    @app.context_processor
    def _inject():
        return {
            "modules": [
                (MODULE_SLUGS[layer], MODULE_TITLES[layer]) for layer in app.config["MODULES"]
            ],
            "user": session.get("user"),
        }

    # -------------------------------------------------------------- routes --

    @app.get("/robots.txt")
    def robots():
        return "User-agent: *\nDisallow: /\n", 200, {"Content-Type": "text/plain"}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            session["login_token"] = secrets.token_urlsafe(16)
            return render_template("login.html", token=session["login_token"], error=None)

        expected = session.get("login_token")
        # A missing token must fail, not match a missing expectation.
        token_ok = bool(expected) and request.form.get("_token") == expected
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if token_ok and app.config["USERS"].get(username) == password:
            session.clear()
            session["user"] = username
            target = request.args.get("next") or url_for("home")
            return redirect(target)
        session["login_token"] = secrets.token_urlsafe(16)
        return render_template(
            "login.html", token=session["login_token"], error="Invalid credentials."
        ), 401

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def home():
        cards = [
            (MODULE_SLUGS[layer], MODULE_TITLES[layer], LAYER_DESCRIPTIONS[layer], len(data[layer]))
            for layer in app.config["MODULES"]
        ]
        return render_template("home.html", cards=cards)

    @app.get("/m/<slug>/")
    @login_required
    def module_list(slug: str):
        layer = layer_or_404(slug)
        rows = data[layer]
        columns = LIST_COLUMNS.get(layer) or list(rows[0].keys())

        query = request.args.get("q", "").strip()
        if query:
            needle = query.lower()
            indexed = [
                (i, row) for i, row in enumerate(rows)
                if any(needle in str(row.get(c, "")).lower() for c in columns)
            ]
        else:
            indexed = list(enumerate(rows))

        size = app.config["PAGE_SIZE"]
        pages = max(1, -(-len(indexed) // size))
        page = request.args.get("page", 1, type=int)
        page = min(max(page, 1), pages)
        chunk = indexed[(page - 1) * size: page * size]

        return render_template(
            "list.html",
            slug=slug,
            title=MODULE_TITLES[layer],
            columns=columns,
            rows=chunk,
            page=page,
            pages=pages,
            total=len(indexed),
            query=query,
        )

    @app.get("/m/<slug>/record/<int:rid>")
    @login_required
    def module_detail(slug: str, rid: int):
        layer = layer_or_404(slug)
        rows = data[layer]
        if not 0 <= rid < len(rows):
            abort(404)
        return render_template(
            "detail.html",
            slug=slug,
            title=MODULE_TITLES[layer],
            rid=rid,
            record=rows[rid],
            prev_id=rid - 1 if rid > 0 else None,
            next_id=rid + 1 if rid + 1 < len(rows) else None,
        )

    return app


__all__ = [
    "create_app", "DEFAULT_USERS", "LIST_COLUMNS", "MODULE_SLUGS", "MODULE_TITLES",
]
