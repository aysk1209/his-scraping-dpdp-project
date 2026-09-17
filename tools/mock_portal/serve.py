"""Run the portal in a background thread, for tests and demo scripts.

    with BackgroundPortal(source) as portal:
        PortalHISDataSource(portal.url, portal.username, portal.password)
"""

from __future__ import annotations

import logging
import socket
import threading
from typing import Any

from werkzeug.serving import make_server

from extraction.base import HISDataSource
from tools.mock_portal import DEFAULT_USERS, create_app


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class BackgroundPortal:
    """Serve ``create_app(source, **app_kwargs)`` on a free local port in a thread."""

    def __init__(
        self,
        source: HISDataSource,
        *,
        port: int | None = None,
        users: dict[str, str] | None = None,
        tls: bool = True,
        **app_kwargs: Any,
    ) -> None:
        self.users = dict(users or DEFAULT_USERS)
        self.app = create_app(source, users=self.users, **app_kwargs)
        self.port = port or free_port()
        # Served over TLS by default with a throwaway self-signed certificate, so
        # the scraper's connection is encrypted the way a real portal's would be
        # and the adapter can *observe* it rather than assume it. ``tls=False``
        # serves plain http -- and the compliant technique then declares that.
        self.tls = tls
        self.url = f"{'https' if tls else 'http'}://127.0.0.1:{self.port}"
        # The per-request access log would drown the demo output; the portal is a
        # fixture, so the browser's page-load count is the record of what was fetched.
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        self._server = make_server(
            "127.0.0.1", self.port, self.app, threaded=True,
            ssl_context="adhoc" if tls else None,
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def username(self) -> str:
        return next(iter(self.users))

    @property
    def password(self) -> str:
        return self.users[self.username]

    def __enter__(self) -> "BackgroundPortal":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._server.shutdown()
        self._thread.join(timeout=5)
