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


def sample_records(source, layers, n: int = 2, fields: int = 5, width: int = 20) -> str:
    """A few illustrative synthetic rows, straight from the data source.

    Trimmed to the first ``fields`` columns and short values so each row fits on
    one line.
    """

    lines = [
        "sample synthetic records "
        "(illustrative -- scoring uses field categories, not values):"
    ]
    for layer in layers:
        lines.append(f"  {layer.value}:")
        for row in list(source.fetch(layer))[:n]:
            items = list(row.items())
            shown = ", ".join(
                f"{key}={str(val)[: width - 1] + '…' if len(str(val)) > width else val}"
                for key, val in items[:fields]
            )
            extra = f"  (+{len(items) - fields} more)" if len(items) > fields else ""
            lines.append(f"    {shown}{extra}")
    return "\n".join(lines)
