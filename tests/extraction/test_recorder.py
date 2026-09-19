"""The recorder's rationing: pacing to a per-minute allowance and a per-day
budget that is remembered across runs, so a free-tier model is recorded over
several days without ever running the allowance out mid-session."""

from __future__ import annotations

import json

import scripts.record_ai_agents as rec


def test_the_daily_ledger_is_per_model_and_per_day(tmp_path, monkeypatch):
    monkeypatch.setattr(rec, "QUOTA_LEDGER", tmp_path / ".quota.json")
    assert rec.quota_used("gemini-3.8-flash") == 0
    rec.quota_note("gemini-3.8-flash", 7)
    assert rec.quota_used("gemini-3.8-flash") == 7
    assert rec.quota_used("gemini-3.1-flash-lite") == 0
    # Yesterday's count does not carry over.
    data = json.loads((tmp_path / ".quota.json").read_text(encoding="utf-8"))
    data["gemini-3.8-flash"] = {"2000-01-01": 20}
    (tmp_path / ".quota.json").write_text(json.dumps(data), encoding="utf-8")
    assert rec.quota_used("gemini-3.8-flash") == 0


def test_pacing_follows_the_models_allowance():
    rpm, rpd = rec.MODEL_LIMITS["gemini-3.8-flash"]
    assert (rpm, rpd) == (5, 20)
    pacer = rec.Pacer(rpm)
    assert pacer.gap == 60 / 5 + 1                      # 13 s between calls: never provokes a 429
    pacer.mark()
    pacer.gap = 0.05
    pacer.wait()                                        # returns after the gap, does not raise


def test_a_daily_cap_error_is_told_apart_from_a_rate_limit():
    class Boom(Exception):
        pass

    calls = {"n": 0}

    def daily():
        calls["n"] += 1
        raise Boom("429 RESOURCE_EXHAUSTED: Quota exceeded for metric 'GenerateRequestsPerDayPerProjectPerModel'")

    try:
        rec._with_backoff(daily, attempts=3)
        assert False
    except rec.DailyCapReached:
        assert calls["n"] == 1                           # not retried: nothing more will succeed today
