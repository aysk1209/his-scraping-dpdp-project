"""Draw the README's result figures from the committed benchmark artefacts.

    python scripts/make_readme_figures.py

Writes ``assets/traps.svg`` (trap runs held, in-memory benchmark), ``assets/pageloads.svg``
(page loads against the portal) and ``assets/banner.svg``. Nothing is typed in: every bar
is read from ``docs/benchmark_results/benchmark.json`` / ``benchmark-portal.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "docs" / "benchmark_results"
OUT = ROOT / "assets"
INK, MUTE, GRID, BG = "#0f172a", "#64748b", "#e2e8f0", "#ffffff"
HUE = {"ours": "#0d9488", "baseline": "#94a3b8", "claude": "#4f46e5", "gemini": "#d97706"}
FONT = "font-family=\"Inter,Segoe UI,Helvetica,Arial,sans-serif\""


def rows(name: str) -> list[dict]:
    data = json.loads((RES / name).read_text(encoding="utf-8"))["scores"]
    return [s for s in data if s["briefing"] in (None, "policy")]


def hue(s: dict) -> str:
    n = s["short"]
    return HUE["ours"] if n.startswith("compliance") else HUE["baseline"] if n.startswith("uncons") \
        else HUE["gemini"] if n.startswith("gemini") else HUE["claude"]


def label(s: dict) -> str:
    n = s["short"].removesuffix("-policy")
    return "ours (reference)" if n.startswith("compliance") else "baseline" if n.startswith("uncons") else n


def bars(title: str, sub: str, items: list[tuple[str, float, str, str]], top: float) -> str:
    w, left, h = 760, 210, 70 + 38 * len(items)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" {FONT}>',
           f'<rect width="{w}" height="{h}" rx="14" fill="{BG}" stroke="{GRID}"/>',
           f'<text x="24" y="34" font-size="17" font-weight="700" fill="{INK}">{title}</text>',
           f'<text x="24" y="54" font-size="12" fill="{MUTE}">{sub}</text>']
    for i, (name, v, txt, col) in enumerate(items):
        y = 78 + 38 * i
        out.append(f'<text x="{left - 12}" y="{y + 17}" font-size="13" text-anchor="end" fill="{INK}">{name}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{w - left - 90}" height="24" rx="5" fill="#f1f5f9"/>')
        bw = max(3, (w - left - 90) * v / top)
        out.append(f'<rect x="{left}" y="{y}" width="{bw:.1f}" height="24" rx="5" fill="{col}"/>')
        out.append(f'<text x="{left + bw + 8:.1f}" y="{y + 17}" font-size="13" font-weight="600" fill="{INK}">{txt}</text>')
    return "\n".join(out) + "\n</svg>\n"


def banner() -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 300" width="1200" height="300" {FONT}>
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1220"/><stop offset="1" stop-color="#134e4a"/></linearGradient></defs>
<rect width="1200" height="300" rx="18" fill="url(#g)"/>
<g stroke="#2dd4bf" stroke-opacity=".18">{"".join(f'<line x1="{x}" y1="0" x2="{x - 140}" y2="300"/>' for x in range(300, 1400, 60))}</g>
<g fill="none" stroke="#5eead4" stroke-width="3" stroke-linecap="round">
<rect x="70" y="86" width="86" height="86" rx="14"/><path d="M99 129h28M113 115v28"/>
<path d="M156 129h70"/><circle cx="244" cy="129" r="16"/><path d="M262 129h70"/>
<path d="M332 100l38 29-38 29z"/><path d="M370 129h60"/><path d="M430 104h44v50h-44z"/><path d="M440 118h24M440 130h24M440 142h14"/></g>
<text x="70" y="230" font-size="40" font-weight="700" fill="#f8fafc">DPDP-compliant HIS data extraction</text>
<text x="70" y="262" font-size="18" fill="#99f6e4">Seven rules of India's DPDP Act 2023, executable, benchmarked on every technique</text>
</svg>
'''


def main() -> None:
    OUT.mkdir(exist_ok=True)
    mem = rows("benchmark.json")
    items = [(label(s), s["traps_resisted"], f'{s["traps_resisted"]} / {s["traps"]}', hue(s)) for s in mem]
    (OUT / "traps.svg").write_text(bars(
        "Trap runs held against the purpose policy",
        "20 runs per technique (4 trap jobs x 5); models are told the policy. More is better.",
        items, max(s["traps"] for s in mem)), encoding="utf-8")
    por = rows("benchmark-portal.json")
    items = [(label(s), s["cost"]["page_loads"], f'{s["cost"]["page_loads"]} loads', hue(s)) for s in por]
    (OUT / "pageloads.svg").write_text(bars(
        "Page loads to do the same jobs on the login-gated portal",
        "Real browser, real pagination. Fewer is cheaper; the baseline reads every page.",
        items, max(i[1] for i in items)), encoding="utf-8")
    (OUT / "banner.svg").write_text(banner(), encoding="utf-8")
    print("wrote", ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
