"""Serve the mock HIS portal.

    python -m tools.mock_portal                      # 200 records/layer, seed 42, :8765
    python -m tools.mock_portal --records 5000       # large enough to page for a while
    python -m tools.mock_portal --latency-ms 40      # feel like a remote system

Sign in with frontdesk / letmein (override with --user NAME:PASSWORD).
"""

from __future__ import annotations

import argparse

from extraction.adapters.mock_his import MockHISDataSource
from tools.mock_portal import DEFAULT_USERS, create_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve the mock HIS portal (test fixture).")
    parser.add_argument("--records", type=int, default=200, help="records per layer")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--latency-ms", type=int, default=0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--user", action="append", default=[],
                        help="NAME:PASSWORD; repeatable; replaces the default account")
    args = parser.parse_args(argv)

    users = dict(u.split(":", 1) for u in args.user) if args.user else DEFAULT_USERS
    source = MockHISDataSource(records_per_layer=args.records, seed=args.seed)
    app = create_app(source, users=users, page_size=args.page_size, latency_ms=args.latency_ms)

    print(f"mock HIS portal on http://{args.host}:{args.port}/  "
          f"({args.records} records/layer, seed {args.seed}, {args.latency_ms} ms latency)")
    print("accounts: " + ", ".join(f"{u} / {p}" for u, p in users.items()))
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
