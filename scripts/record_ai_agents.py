"""Ask the public AI agents to decide each benchmark task, and record what they said.

    set ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY   (whichever you have)
    python scripts/record_ai_agents.py                       # every keyed provider, all three briefings
    python scripts/record_ai_agents.py --provider gemini --model <model-id> \
        --briefing policy --briefing unaided --repeats 3     # a further model: its own recording, its own
                                                             # row (shown at 'policy'); resumes across days.
                                                             # (gemini-3.8-flash was tried 2026-09-22: the free
                                                             # tier served 1-2 calls a day; dropped, no credit.)
    python scripts/record_ai_agents.py --provider claude --repeats 5
    python scripts/record_ai_agents.py --briefing informed --overwrite

One live call per provider x briefing x task x repeat. Each decision -- the
fields the model chose and the manifest it declared, nothing more -- is appended
to ``src/extraction/techniques/recordings/<provider>--<model>--<briefing>.json``. From then
on every demo and the benchmark replay those decisions without network or keys,
and the benchmark's determinism column is computed from the samples.

Free tiers ration calls per minute and per day, so the recorder is built to be
interrupted and resumed without waste:

- **Paced.** Calls are spaced to the model's requests-per-minute allowance
  (``MODEL_LIMITS``, or ``--rpm``) from the time of the last call, so a run
  never provokes a rate limit it then has to back off from.
- **Budgeted.** A per-model ledger (``recordings/.quota.json``, git-ignored)
  counts today's calls; the run stops *before* the daily allowance
  (``--daily-budget``) is spent and says when to resume. A daily-cap error
  from the provider marks the day spent.
- **Breadth-first.** Samples are taken one per task across all tasks before a
  second sample of any -- so a day that ends early still leaves every task
  with the same number of samples, and the model enters the tables with what
  it has (the benchmark caps its repeats at the samples recorded). The
  ``policy`` briefing is recorded first, being the one the tables lead with.
- **Resumable.** ``--repeats`` is a target; the same command re-run picks up
  at the first missing sample.

No patient value is ever sent: the model is briefed with field *names*. The
recordings are therefore safe to commit, and they are committed, so that the
review-room demo does not depend on the venue's Wi-Fi.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present
from compliance.capabilities import DEFAULT_REGISTER
from compliance.checkers import run_all
from compliance.veracity import verify
from extraction.adapters.mock_his import MockHISDataSource
from extraction.techniques.ai_agent import RECORDINGS_DIR, BRIEFINGS, AIAgentTechnique
from extraction.techniques.ai_providers import (
    EXPLICIT_ONLY, PROVIDERS, ProviderUnavailable, key_available, list_models, model_for,
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
    cap_probes = 0
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
            # today. But the server sometimes says "retry in 29s" with it -- a
            # sliding window, not a calendar day. Probe that hint up to three
            # times (it costs nothing if the cap is real), then stop cleanly;
            # the run resumes where it left off after the reset.
            if any(k in text for k in ("PerDay", "per day", "perDay", "daily", "Daily")):
                m = re.search(r"retry in ([0-9.]+)\s*s", text)
                if m and cap_probes < 3 and float(m.group(1)) <= 300:
                    cap_probes += 1
                    wait = float(m.group(1)) + 2.0
                    print(f"    daily cap reported with a retry hint -- probing it in {wait:.0f} s "
                          f"({cap_probes}/3)")
                    time.sleep(wait)
                    continue
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


# Free-tier allowances per model id, as published at the time of recording
# (requests per minute, requests per day). Overridable with --rpm / --daily-budget;
# an unknown model is paced conservatively.
MODEL_LIMITS: dict[str, tuple[int, int]] = {
    "gemini-3.8-flash": (5, 20),
    "gemini-3.1-flash-lite": (15, 500),
    # Through a Claude subscription (claude-code): gentle pacing, inside a usage window.
    "claude-haiku-4-5": (6, 200),
    "claude-sonnet-5": (6, 200),
}
DEFAULT_LIMITS = (5, 50)
QUOTA_LEDGER = RECORDINGS_DIR / ".quota.json"


# The free tier's "per day" is the provider's day, not ours: it resets at
# midnight Pacific time (12:30 IST during daylight time, 13:30 otherwise). The
# ledger is keyed on that day so a run after the reset is not refused by a
# local date that has not changed -- or allowed by one that has.
def _provider_now():
    from datetime import datetime, timedelta, timezone
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles"))
    except Exception:                                              # noqa: BLE001 - no tz database (Windows without tzdata)
        return datetime.now(timezone.utc) - timedelta(hours=7)     # PDT; an hour off in winter, on the safe side


def _today() -> str:
    return _provider_now().date().isoformat()


def reset_note() -> str:
    """When the provider's day turns, in local time."""

    from datetime import datetime, timedelta
    now = _provider_now()
    reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    local = reset.astimezone().strftime("%H:%M %Z on %d.%m")
    return f"the provider's day resets at midnight Pacific -- {local} local time"


def quota_used(model: str) -> int:
    """Calls made to ``model`` today, per the local ledger."""

    try:
        data = json.loads(QUOTA_LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    return int(data.get(model, {}).get(_today(), 0))


def quota_note(model: str, n: int) -> None:
    try:
        data = json.loads(QUOTA_LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault(model, {})
    data[model] = {_today(): n}                     # only today matters; older days are dropped
    QUOTA_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_LEDGER.write_text(json.dumps(data, indent=2), encoding="utf-8")


class Pacer:
    """Space calls to a requests-per-minute allowance, measured from the last call."""

    def __init__(self, rpm: int) -> None:
        import time
        self.gap = 60.0 / max(1, rpm) + 1.0
        self._last: float | None = None
        self._time = time

    def wait(self) -> None:
        if self._last is not None:
            due = self._last + self.gap - self._time.monotonic()
            if due > 0:
                self._time.sleep(due)

    def mark(self) -> None:
        self._last = self._time.monotonic()


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
    parser.add_argument("--rpm", type=int, help="requests per minute to pace to (default: the model's known allowance)")
    parser.add_argument("--daily-budget", type=int,
                        help="calls to allow today for this model (default: the model's known allowance); "
                             "the run stops before exceeding it and resumes tomorrow")
    parser.add_argument("--pause", type=float, default=None,
                        help="fixed seconds between calls, overriding the pacing derived from --rpm")
    args = parser.parse_args()

    # A subscription-backed provider is used only when named (--provider claude-code).
    providers = args.provider or [p for p in PROVIDERS if p not in EXPLICIT_ONLY and key_available(p)]
    briefings = args.briefing or list(BRIEFINGS)
    if not providers:
        sys.exit("No provider key found. Set ANTHROPIC_API_KEY, OPENAI_API_KEY or GEMINI_API_KEY.")
    if args.list_models:
        show_models(providers)
        return

    # The headline briefing first: a day that ends early still yields the row
    # the tables lead with.
    briefings = sorted(briefings, key=lambda b: 0 if b == "policy" else 1)

    print(present.banner("Recording AI-agent decisions"))
    print(f"  providers : {', '.join(f'{p} ({args.model or model_for(p)})' for p in providers)}")
    print(f"  briefings : {', '.join(briefings)}  (breadth-first: one sample of every task, then the next)")
    print(f"  tasks     : {', '.join(t.task_id for t in TASKS)}   x {args.repeats} repeat(s)")
    print("  The model is shown field names and the job; no patient value leaves this machine.")

    # A small in-memory source is enough: the agent decides from the schema, and
    # the schema is the same whatever the volume.
    source = MockHISDataSource(records_per_layer=5, seed=42)
    from compliance.benchmark import bind_subject
    tasks = bind_subject(TASKS, source)

    for provider in providers:
        model = args.model or model_for(provider)
        rpm, rpd = MODEL_LIMITS.get(model, DEFAULT_LIMITS)
        rpm = args.rpm or rpm
        budget = args.daily_budget or rpd
        used = quota_used(model)
        pacer = Pacer(rpm)
        if args.pause is not None:
            pacer.gap = args.pause
        print(present.rule())
        print(f"  {model}: paced to {rpm}/min ({pacer.gap:.0f} s between calls); "
              f"today's budget {budget}, {used} used, {max(0, budget - used)} left")
        capped = used >= budget
        if capped:
            print("  today's budget is spent -- re-run tomorrow; nothing to do now")
        for briefing in briefings:
            if capped:
                break
            tech = AIAgentTechnique(provider, briefing=briefing, mode="live", model=model)
            print(present.rule())
            print(f"{tech.name}  ->  {tech.recording_path.name}")
            if args.overwrite and tech.recording_path.exists():
                data = tech._load()
                data["tasks"] = {}
                tech.recording_path.write_text(__import__("json").dumps(data, indent=2), encoding="utf-8")
            # Resume: samples already recorded under today's exact brief count
            # toward the target; stale ones (a different brief) do not.
            have: dict[str, int] = {}
            for task in tasks:
                fresh = task.task_id not in tech.stale_tasks(source, [task])
                have[task.task_id] = len(tech.recorded_samples(task.task_id)) if fresh else 0
            remaining = sum(max(0, args.repeats - n) for n in have.values())
            if remaining == 0:
                print(f"  complete: {args.repeats} sample(s) per task already recorded under this brief")
                continue
            left = max(0, budget - used)
            print(f"  {remaining} call(s) to make ({sum(have.values())} already on file); "
                  f"{min(remaining, left)} of them fit in today's budget")
            # Breadth-first: sample i of every task before sample i+1 of any.
            for i in range(args.repeats):
                if capped:
                    break
                for task in tasks:
                    if have[task.task_id] > i:
                        continue
                    if used >= budget:
                        print(f"  today's budget ({budget}) is spent. Re-run the same command after the reset "
                              f"({reset_note()}); it resumes at {task.task_id}, sample {i + 1}.")
                        capped = True
                        break
                    pacer.wait()
                    try:
                        out = _with_backoff(lambda: tech.extract(source, task), pause=0.0)
                    except DailyCapReached as exc:
                        used = budget
                        quota_note(model, used)
                        print(f"  {task.task_id:<22} daily cap reached: {exc}")
                        print(f"  stopping for today ({reset_note()}). Re-run the same command after the reset; "
                              f"it resumes here. The cap is per Google Cloud project, not per key.")
                        capped = True
                        break
                    except ProviderUnavailable as exc:
                        print(f"  {task.task_id:<22} unavailable: {exc}")
                        capped = True
                        break
                    except Exception as exc:                       # noqa: BLE001 - report and continue
                        pacer.mark()
                        print(f"  {task.task_id:<22} run {i + 1}: {type(exc).__name__}: {str(exc)[:160]}")
                        continue
                    pacer.mark()
                    used += 1
                    quota_note(model, used)
                    have[task.task_id] += 1
                    d = tech.last_decision
                    report = run_all(out.run, out.records)
                    fields = sum(len(v) for v in d.selection().values())
                    unknown = len(d.unknown_fields())
                    ver = verify(out.run, DEFAULT_REGISTER)
                    print(
                        f"  {task.task_id:<22} run {i + 1} [{used}/{budget} today]: {fields} fields"
                        + (f" (+{unknown} unknown, dropped)" if unknown else "")
                        + f", score {report.compliance_score:.3f}, "
                        f"{report.rules_passed}/{len(report.results)} rules"
                        + (f", {len(ver.unsubstantiated)} unbacked claim(s)" if ver.unsubstantiated else "")
                        + (f"  [trap: {task.trap}]" if task.trap else "")
                    )
                    if d.rationale:
                        print(f"  {'':<22}   \"{d.rationale.strip()[:110]}\"")

    print(present.rule())
    print("Recordings written. The benchmark and every demo now replay them; a model enters the tables")
    print("as soon as every task has one sample (repeats are capped at what is recorded). Re-run the same")
    print("command to add samples up to --repeats; --overwrite after changing a task or a prompt.")


if __name__ == "__main__":
    main()
