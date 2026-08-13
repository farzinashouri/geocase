"""Pacing and quota tests (Plan 17 §1.1-1.2). Nothing here sleeps for real."""

from __future__ import annotations

import json

import httpx
import pytest

from geocase.benchmark.runner.limiter import (
    DailyQuota,
    QuotaExhaustedError,
    RateLimiter,
)
from geocase.benchmark.runner.openrouter import (
    ChatFailedError,
    OpenRouterClient,
    RetryPolicy,
)

# ---------------------------------------------------------------- limiter


def test_rate_limiter_disabled_when_rpm_is_none():
    assert RateLimiter(None).acquire() == 0.0


def test_rate_limiter_rejects_non_positive_rpm():
    with pytest.raises(ValueError):
        RateLimiter(0)


def test_rate_limiter_spaces_requests(monkeypatch):
    """The second request waits ~1/rate; the first goes through immediately."""
    clock = {"t": 1000.0}
    slept: list[float] = []
    monkeypatch.setattr(
        "geocase.benchmark.runner.limiter.time.monotonic", lambda: clock["t"]
    )

    def fake_sleep(s):
        slept.append(s)
        clock["t"] += s

    monkeypatch.setattr("geocase.benchmark.runner.limiter.time.sleep", fake_sleep)

    limiter = RateLimiter(60)  # one request per second
    assert limiter.acquire() == 0.0
    waited = limiter.acquire()
    assert slept and waited == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------- quota


def test_daily_quota_raises_when_exhausted(tmp_path):
    quota = DailyQuota(tmp_path / "q.json", 2)
    quota.take()
    quota.take()
    assert quota.remaining == 0
    with pytest.raises(QuotaExhaustedError):
        quota.take()


def test_daily_quota_persists_across_instances(tmp_path):
    """A same-day re-run must not re-spend a quota already burnt."""
    path = tmp_path / "q.json"
    DailyQuota(path, 3).take(2)
    assert DailyQuota(path, 3).used == 2
    with pytest.raises(QuotaExhaustedError):
        DailyQuota(path, 3).take(2)


def test_daily_quota_resets_on_a_new_day(tmp_path):
    path = tmp_path / "q.json"
    path.write_text(json.dumps({"date": "1999-01-01", "count": 99}))
    assert DailyQuota(path, 5).used == 0


def test_daily_quota_disabled_when_limit_is_none(tmp_path):
    quota = DailyQuota(tmp_path / "q.json", None)
    quota.take(10_000)
    assert quota.remaining is None


# ---------------------------------------------------------------- retry policy


def _client(handler, **kwargs):
    return OpenRouterClient(
        api_key="test-key", transport=httpx.MockTransport(handler), **kwargs
    )


def test_long_retry_after_still_raises_by_default(monkeypatch):
    """Off by default: a long silent sleep is indistinguishable from a hang."""
    monkeypatch.setattr(
        "geocase.benchmark.runner.openrouter.time.sleep", lambda s: None
    )
    client = _client(
        lambda request: httpx.Response(429, headers={"retry-after": "24"}),
        policy=RetryPolicy(max_retry_after=10.0),
    )
    with pytest.raises(ChatFailedError, match="longer than this run will wait"):
        client.chat("test/model", [{"role": "user", "content": "hi"}])


def test_honored_long_retry_after_sleeps_instead_of_failing(monkeypatch):
    """The 2026-08-11 failure: Retry-After: 24 against max_retry_after 10."""
    slept: list[float] = []
    monkeypatch.setattr("geocase.benchmark.runner.openrouter.time.sleep", slept.append)
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 2:
            return httpx.Response(429, headers={"retry-after": "24"})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"cost": 0.0},
            },
        )

    client = _client(
        handler,
        policy=RetryPolicy(
            max_retry_after=10.0,
            honor_long_retry_after=True,
            max_total_seconds=600.0,
        ),
    )
    assert client.chat("m", [{"role": "user", "content": "hi"}]).content == "ok"
    assert slept == [24.0]


def test_honored_retry_after_is_not_clamped_by_max_backoff(monkeypatch):
    """max_backoff=60 must not clamp an honored 300s ask (that is why
    max_backoff_long exists)."""
    slept: list[float] = []
    monkeypatch.setattr("geocase.benchmark.runner.openrouter.time.sleep", slept.append)
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 2:
            return httpx.Response(429, headers={"retry-after": "300"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}], "usage": {}},
        )

    client = _client(
        handler,
        policy=RetryPolicy(
            max_retry_after=10.0,
            honor_long_retry_after=True,
            max_backoff=60.0,
            max_backoff_long=300.0,
            max_total_seconds=6000.0,
        ),
    )
    client.chat("m", [{"role": "user", "content": "hi"}])
    assert slept == [300.0], "an honored long wait was clamped to max_backoff"


def test_every_attempt_including_retries_consumes_quota(tmp_path, monkeypatch):
    """A retry spends the same account-wide budget as a first attempt."""
    monkeypatch.setattr(
        "geocase.benchmark.runner.openrouter.time.sleep", lambda s: None
    )
    quota = DailyQuota(tmp_path / "q.json", 10)
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}], "usage": {}},
        )

    client = _client(handler, policy=RetryPolicy(backoff_base=0.0), quota=quota)
    client.chat("m", [{"role": "user", "content": "hi"}])
    assert quota.used == 3, "retries did not consume quota"


def test_quota_exhaustion_stops_the_call(tmp_path):
    quota = DailyQuota(tmp_path / "q.json", 1)
    quota.take()
    client = _client(lambda r: httpx.Response(200, json={}), quota=quota)
    with pytest.raises(QuotaExhaustedError):
        client.chat("m", [{"role": "user", "content": "hi"}])
