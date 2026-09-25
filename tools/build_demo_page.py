"""Build the Review-II "rules vs just AI" page.

    python tools/build_demo_page.py

``docs/benchmark_results/rules-vs-just-ai.html`` is a single self-contained
page, rendered from ``tools/rules_page.html`` with the shared look of the other
demo pages (``tools/page_kit.py``). Its charts read one JSON block, built here
from the committed artefacts -- ``benchmark.json`` (in memory, eight tasks, five
repeats), ``benchmark-portal.json`` (the live pipeline), the recorded agent
decisions, the task definitions and the field catalogue. Run it after
``scripts/run_benchmark.py`` or ``run_pipeline.py`` so the page and the tables
never disagree.

Nothing personal is embedded: field names, categories, scores and manifest
structure only. Rationales are the model's own words about field names.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from compliance.benchmark import manifest_structure                      # noqa: E402
from compliance.checkers import run_all                                  # noqa: E402
from compliance.policy import PURPOSE_POLICY                             # noqa: E402
from compliance.rules import ALL_RULES                                   # noqa: E402
from data_synthetic.catalogue import FIELD_CATALOGUE                     # noqa: E402
from extraction.adapters.mock_his import MockHISDataSource               # noqa: E402
from extraction.techniques.ai_agent import (  # noqa: E402
    AIAgentTechnique, BRIEFING_LABELS, BRIEFINGS, model_slug, recorded_models,
)
from extraction.techniques.ai_providers import PROVIDERS            # noqa: E402
from run_benchmark import TASKS                                          # noqa: E402
from tools.page_kit import render, write                                 # noqa: E402

PAGE = ROOT / "docs" / "benchmark_results" / "rules-vs-just-ai.html"
TEMPLATE = ROOT / "tools" / "rules_page.html"
RESULTS = ROOT / "docs" / "benchmark_results"


def _score_fields(technique_short: str, scores: list[dict]) -> dict:
    return next(s for s in scores if s["short"] == technique_short)


def _short_model(model: str) -> str:
    """'gemini-3.1-flash-lite' -> '3.1-flash-lite'; 'claude-haiku-4-5' -> 'haiku-4-5'."""

    for family in ("gemini-", "claude-", "gpt-"):
        if model.startswith(family):
            return model[len(family):]
    return model


def _agents() -> list[dict]:
    """Every recorded provider x model x briefing, in table order: model, then briefing order."""

    out: list[dict] = []
    for provider in PROVIDERS:
        for model in sorted({m for b in BRIEFINGS for m in recorded_models(provider, b)}):
            for briefing in BRIEFINGS:
                if model in recorded_models(provider, briefing):
                    out.append({"k": f"{model_slug(model)}-{briefing}", "provider": provider, "model": model,
                                "briefing": briefing, "name": f"{_short_model(model)}, {BRIEFING_LABELS[briefing]}"})
    return out


def _runs_for(task, provider: str, model: str, briefing: str, source) -> list[dict]:
    """Every recorded decision for the task, replayed and scored; [] if stale or incomplete."""

    tech = AIAgentTechnique(provider, briefing=briefing, mode="replay", model=model)
    if tech.stale_tasks(source, [task]) or not tech.has_recording(task.task_id):
        return []
    out: list[dict] = []
    policy = PURPOSE_POLICY[task.purpose]
    for i, _ in enumerate(tech.recorded_samples(task.task_id)):
        tech.sample = i
        result = tech.extract(source, task)
        decision = tech.last_decision
        assert decision is not None
        report = run_all(result.run, result.records)
        pulled = {f"{layer.value}/{name}" for layer, names in decision.selection().items() for name in names}
        categories = {c for r in result.records for c in r.field_categories}
        out.append({
            "fields": sorted(pulled),
            "score": round(report.compliance_score, 3),
            "oos": sorted(c.value for c in categories - policy.allowed_categories),
            "onward": list(result.run.secondary_uses),
            "retention": result.run.retention_days,
            "rationale": decision.rationale.strip()[:160],
            "structure": manifest_structure(result.run),
        })
    return out


def build_data() -> dict:
    memory = json.loads((RESULTS / "benchmark.json").read_text(encoding="utf-8"))
    portal = json.loads((RESULTS / "benchmark-portal.json").read_text(encoding="utf-8"))
    source = MockHISDataSource(records_per_layer=5, seed=42)
    from compliance.benchmark import bind_subject
    bound = bind_subject(TASKS, source)
    # Only agents the benchmark itself admitted (a fresh recording for every task).
    admitted = {s["short"] for s in memory["scores"]}
    agents = [a for a in _agents() if a["k"] in admitted]

    tasks: dict[str, dict] = {}
    for task in bound:
        policy = PURPOSE_POLICY[task.purpose]
        tasks[task.task_id] = {
            "purpose": task.purpose.value,
            "description": task.description,
            "trap": task.trap,
            "needed": sorted(f"{layer}/{name}" for layer, name in task.field_refs()),
            "allowed": sorted(c.value for c in policy.allowed_categories),
            "ceiling": policy.max_retention_days,
            "runs": {a["k"]: _runs_for(task, a["provider"], a["model"], a["briefing"], source) for a in agents},
        }

    catalogue = {layer.value: {name: cat.value for name, cat in fields.items()}
                 for layer, fields in FIELD_CATALOGUE.items()}
    return {
        "rules": [r.rule_id for r in ALL_RULES],
        "memory": memory["scores"],
        "portal": portal["scores"],
        "tasks": tasks,
        "agents": agents,
        "catalogue": catalogue,
        "meta": {
            "generated": memory["generated_at"][:10],
            "repeats": memory["scores"][0].get("repeats", 1),
            # A model is repeated at most as often as it has recordings: say so per model.
            "repeats_by_model": {m: max(s.get("repeats", 1) for s in memory["scores"] if s.get("model") == m)
                                 for m in {s["model"] for s in memory["scores"] if s.get("model")}},
            "tasks": len(memory["task_ids"]),
            "models": sorted({a["model"] for a in agents}),
            "briefings": [BRIEFING_LABELS[b] for b in BRIEFINGS if any(a["briefing"] == b for a in agents)],
        },
    }


def main() -> None:
    data = build_data()
    write(PAGE, render(TEMPLATE, data, current="rules", out=PAGE))
    meta = data["meta"]
    size = len(json.dumps(data, separators=(",", ":")))
    print(f"wrote {PAGE}  ({size / 1024:.0f} KB of data; {meta['tasks']} tasks, {meta['repeats']} repeats, "
          f"agents: {', '.join(a['k'] for a in data['agents']) or 'none'})")


if __name__ == "__main__":
    main()
