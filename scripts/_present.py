"""Shared console presentation helpers for the demo scripts.

Keeps the three demos visually consistent: a banner, a one-line takeaway, and a
uniform way of reporting written artifacts.
"""

from __future__ import annotations

from pathlib import Path

_WIDTH = 74


def banner(title: str) -> str:
    bar = "=" * _WIDTH
    return f"\n{bar}\n  {title}\n{bar}"


def takeaway(text: str) -> str:
    return f"\n>>> {text}\n"


def wrote(path: Path) -> str:
    return f"    wrote {path}"


def rule() -> str:
    return "-" * _WIDTH
