"""Ask the public AI agents to decide each benchmark task, and record what they said.

    set ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY   (whichever you have)
    python scripts/record_ai_agents.py                       # every keyed provider, all three briefings
    python scripts/record_ai_agents.py --provider gemini --model gemini-3.8-flash \
        --briefing policy --briefing unaided --repeats 3     # a further model: its own recording, its own
                                                             # row (shown at 'policy'); resumes across days
    python scripts/record_ai_agents.py --provider claude --repeats 5
    python scripts/record_ai_agents.py --briefing informed --overwrite

One live call per provider x briefing x task x repeat. Each decision -- the
fields the model chose and the manifest it declared, nothing more -- is appended
to ``src/extraction/techniques/recordings/<provider>--<model>--<briefing>.json``. From then
on every demo and the benchmark replay those decisions without network or keys,
and the benchmark's determinism column is computed from the samples.

No patient value is ever sent: the model is briefed with field *names*. The
recordings are therefore safe to commit, and they are committed, so that the
review-room demo does not depend on the venue's Wi-Fi.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from compliance.capabilities import DEFAULT_REGISTER
from compliance.checkers import run_all
from compliance.veracity import verify
from extraction.adapters.mock_his import MockHISDataSource
from extraction.techniques.ai_agent import BRIEFINGS, AIAgentTechnique
from extraction.techniques.ai_providers import (
    PROVIDERS, ProviderUnavailable, key_available, list_models, model_for,
)
from run_benchmark import TASKS


def show_models(providers: list[str]) -> None:
    """Print the ids each keyed account can use, so the model choice is not a guess."""

    print(present.banner("Models available to your keys"))
    for provider in providers:
        try:
            ids = list_models(provider)
        except ProviderUnavailable as exc:
            print(f"  {provider:<8} unavailable: {exc}")
            continue
        except Exception as exc:                                   # noqa: BLE001
            print(f"  {provider:<8} {type(exc).__name__}: {exc}")
            continue
        current = model_for(provider)
        mark = "ok" if current in ids else "NOT in list -- set AI_AGENT_MODEL_" + provider.upper()
        print(f"  {provider:<8} default {current}  [{mark}]")
        hint = [i for i in ids if any(k in i for k in ("gpt", "gemini", "claude"))]
        for i in hint[:40]:
            print(f"           {i}")
        if len(hint) > 40:
            print(f"           ... {len(hint) - 40} more")


def _with_backoff(call, attempts: int = 6, pause: float = 0.0):
    """Retry on rate limits and transient server errors; free tiers throttle.

    Honours the server's own "retry in N s" when it gives one, otherwise waits
    10, 20, 40, 80, 160 s. Anything else is raised at once. ``pause`` is a fixed
    gap after every successful call, to stay under a per-minute quota.
    """

    import re
    import time
    delay = 10.0
    for attempt in range(attempts):
        try:
            result = call()
            if pause:
                time.sleep(pause)
            return result
        except ProviderUnavailable:
            raise
        except Exception as exc:                                   # noqa: BLE001
            text = f"{type(exc).__name__}: {exc}"
            # A 429 that means "no credit" is not a rate limit; retrying it
            # only burns minutes. Surface it once, as what it is.
            if "insufficient_quota" in text or "check your plan and billing" in text:
                raise ProviderUnavailable(
                    "the account has no API credit (insufficient_quota) -- not a rate limit; "
                    "add credit or use another provider"
                ) from exc
            # A daily cap is not a rate limit either: nothing more will succeed
            # today. Stop cleanly; the run resumes where it left off tomorrow.
            if any(k in text for k in ("PerDay", "per day", "perDay", "daily", "Daily")):
                raise DailyCapReached(text[:200]) from exc
            transient = any(k in text for k in (
                "429", "RESOURCE_EXHAUSTED", "rate", "Rate", "quota",
                "500", "503", "overloaded", "high demand", "UNAVAILABLE", "InternalServer",
                "timed out", "Timeout", "timeout", "ReadTimeout",
            ))
            if not transient or attempt == attempts - 1:
                raise
            m = re.search(r"retry in ([0-9.]+)\s*s", text)
            wait = float(m.group(1)) + 2.0 if m else delay
            print(f"    throttled ({text[:60]}...) -- waiting {wait:.0f} s")
            time.sleep(wait)
            delay *= 2


class DailyCapReached(ProviderUnavailable):
    """The provider's requests-per-day allowance is spent."""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-models", action="store_true",
                        help="show the model ids each keyed account can use, then exit")
    parser.add_argument("--provider", choices=PROVIDERS, action="append",
                        help="repeatable; default: every provider with a key set")
    parser.add_argument("--briefing", choices=BRIEFINGS, action="append",
                        help="repeatable; default: all three")
    parser.add_argument("--model", help="model id to record (default: the provider's env/default id); "
                        "each model gets its own recording and its own row in every table")
    parser.add_argument("--repeats", type=int, default=3,
                        help="decisions to have per task (the determinism sample); an interrupted run "
                        "resumes up to this count, so the same command can be re-run across days")
    parser.add_argument("--overwrite", action="store_true",
                        help="discard existing samples for these tasks first")
    parser.add_argument("--pause", type=float, default=4.0,
                        help="seconds to wait after each call (free tiers cap requests per minute)")
    args = parser.parse_args()

    providers = args.provider or [p for p in PROVIDERS if key_available(p)]
    briefings = args.briefing or list(BRIEFINGS)
    if not providers:
        sys.exit("No provider key found. Set ANTHROPIC_API_KEY, OPENAI_API_KEY or GEMINI_API_KEY.")
    if args.list_models:
        show_models(providers)
        return

    print(present.banner("Recording AI-agent decisions"))
    print(f"  providers : {', '.join(f'{p} ({args.model or model_for(p)})' for p in providers)}")
    print(f"  briefings : {', '.join(briefings)}")
    print(f"  tasks     : {', '.join(t.task_id for t in TASKS)}   x {args.repeats} repeat(s)")
    print("  The model is shown field names and the job; no patient value leaves this machine.")

    # A small in-memory source is enough: the agent decides from the schema, and
    # the schema is the same whatever the volume.
    source = MockHISDataSource(records_per_layer=5, seed=42)
    from compliance.benchmark import bind_subject
    tasks = bind_subject(TASKS, source)

    for provider in providers:
        capped = False
        for briefing in briefings:
            if capped:
                break
            tech = AIAgentTechnique(provider, briefing=briefing, mode="live", model=args.model)
            print(present.rule())
            print(f"{tech.name}  ->  {tech.recording_path.name}")
            if args.overwrite and tech.recording_path.exists():
                data = tech._load()
                data["tasks"] = {}
                tech.recording_path.write_text(__import__("json").dumps(data, indent=2), encoding="utf-8")
            # Resume: samples already recorded under today's exact brief count
            # toward the target; stale ones (a different brief) do not.
            todo = {}
            for task in tasks:
                have = tech.recorded_samples(task.task_id) if task.task_id not in tech.stale_tasks(source, [task]) else []
                todo[task.task_id] = max(0, args.repeats - len(have))
            remaining = sum(todo.values())
            if remaining == 0:
                print(f"  complete: {args.repeats} sample(s) per task already recorded under this brief")
                continue
            print(f"  {remaining} call(s) to make ({sum(args.repeats for _ in tasks) - remaining} already on file)")
            for task in tasks:
                if capped:
                    break
                for i in range(args.repeats - todo[task.task_id], args.repeats):
                    try:
                        out = _with_backoff(lambda: tech.extract(source, task), pause=args.pause)
                    except DailyCapReached as exc:
                        print(f"  {task.task_id:<22} daily cap reached: {exc}")
                        print(f"  stopping for today. Re-run the same command tomorrow; it resumes at this task.")
                        capped = True
                        break
                    except ProviderUnavailable as exc:
                        print(f"  {task.task_id:<22} unavailable: {exc}")
                        capped = True
                        break
                    except Exception as exc:                       # noqa: BLE001 - report and continue
                        print(f"  {task.task_id:<22} run {i + 1}: {type(exc).__name__}: {str(exc)[:160]}")
                        continue
                    d = tech.last_decision
                    report = run_all(out.run, out.records)
                    fields = sum(len(v) for v in d.selection().values())
                    unknown = len(d.unknown_fields())
                    ver = verify(out.run, DEFAULT_REGISTER)
                    print(
                        f"  {task.task_id:<22} run {i + 1}: {fields} fields"
                        + (f" (+{unknown} unknown, dropped)" if unknown else "")
                        + f", score {report.compliance_score:.3f}, "
                        f"{report.rules_passed}/{len(report.results)} rules"
                        + (f", {len(ver.unsubstantiated)} unbacked claim(s)" if ver.unsubstantiated else "")
                        + (f"  [trap: {task.trap}]" if task.trap else "")
                    )
                    if d.rationale:
                        print(f"  {'':<22}   \"{d.rationale.strip()[:110]}\"")

    print(present.rule())
    print("Recordings written. The benchmark and every demo now replay them; re-run with")
    print("--overwrite after changing a task or a prompt (stale samples are detected by fingerprint).")


if __name__ == "__main__":
    main()
