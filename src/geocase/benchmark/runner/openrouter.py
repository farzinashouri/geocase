"""OpenRouter chat client.

Auth comes from ``OPENROUTER_API_KEY`` only; the client refuses to start
without it, never logs it, and it must never be committed. ``usage.include``
is always requested so cost accounting is live, feeding the budget abort."""

from __future__ import annotations

import os
import random
import sys
import time
from dataclasses import dataclass

import httpx

from geocase.benchmark.runner.limiter import DailyQuota, RateLimiter

BASE_URL = "https://openrouter.ai/api/v1"
RETRYABLE = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class RetryPolicy:
    """The five retry knobs as instance state (Plan 17 Phase 1.1).

    They were class attributes, which meant no CLI flag could reach them: when
    OpenRouter answered ``Retry-After: 24`` against a ``max_retry_after`` of
    10.0, ``chat()`` raised without ever sleeping, and no invocation could fix
    it. The class attributes remain as the defaults these fields are built
    from, so ``client.max_total_seconds = x`` still works.
    """

    max_attempts: int = 5
    max_timeout_attempts: int = 2
    max_retry_after: float = 10.0
    backoff_base: float = 2.0
    max_backoff: float = 60.0
    # Separate from max_backoff on purpose: a 60s per-sleep cap must not clamp
    # an honored `Retry-After: 300` down to 60 and then retry into the same 429.
    max_backoff_long: float = 300.0
    max_total_seconds: float = 120.0
    # Off by default. A run that sleeps 24s x 5 x 26 tasks is indistinguishable
    # from a hang, so honoring a long server ask is always an explicit choice.
    honor_long_retry_after: bool = False


class BudgetExceededError(RuntimeError):
    pass


class ChatFailedError(RuntimeError):
    """Every attempt failed (timeout, rate limit, server error, bad payload).

    A single unlucky task must never kill a 200-call run, so this is recorded
    as a per-task outcome upstream and is never fatal. Only budget aborts are."""


# Kept so older imports/tests still resolve; a timeout is just one failure mode.
ChatTimeoutError = ChatFailedError


class CostTracker:
    """Accumulates OpenRouter's returned usage.cost; hard-aborts over budget."""

    def __init__(self, max_usd: float | None):
        self.max_usd = max_usd
        self.spent = 0.0

    def add(self, cost_usd: float | None) -> None:
        if self.max_usd is not None and self.spent + (cost_usd or 0.0) > self.max_usd:
            raise BudgetExceededError(
                f"budget abort: spent ${self.spent:.4f} + ${cost_usd:.4f} "
                f"would exceed max_usd_total ${self.max_usd:.2f}"
            )
        self.spent += cost_usd or 0.0


@dataclass
class ChatReply:
    content: str
    cost: float | None
    usage: dict


class OpenRouterClient:
    # Free-tier 429s are the dominant failure mode, and they clear on a scale
    # of minutes rather than seconds: with base 2.0 the sleeps are roughly
    # 2, 4, 8, 16, 32s (jittered), so five attempts spans about a minute.
    # Two attempts gave up ~2s after the first 429, which on the free tier
    # means giving up immediately.
    max_attempts = 5
    max_timeout_attempts = 2  # timeouts are far costlier to retry than 429s
    # A 429 whose Retry-After is longer than this is a quota that will not
    # clear inside the run: fail the task immediately and let the caller's
    # give-up-after logic skip the model. Sitting through a 60s server-
    # requested wait, five times, is how a run comes to look frozen.
    max_retry_after = 10.0
    backoff_base = 2.0  # seconds; exponential with jitter
    max_backoff = 60.0  # cap per sleep, incl. a server-supplied Retry-After
    # Only ever applied to an *honored* long Retry-After; max_backoff would
    # otherwise clamp a 300s server ask to 60s and retry into the same 429.
    max_backoff_long = 300.0
    honor_long_retry_after = False  # opt-in; see RetryPolicy

    # A whole task must not be able to outlive this, however attempts and
    # timeouts interact. Without it, five attempts against a model that stalls
    # for the full read timeout is a five-minute wait on one prose completion.
    max_total_seconds = 120.0

    # Default budget for one *task* in a long batch run. 120s is the ceiling
    # for a deliberate single call; a 156-call probe cannot afford that per
    # task when a model is rate-limited, so the scripts lower it.
    batch_total_seconds = 20.0

    def __init__(
        self,
        api_key: str | None = None,
        *,
        policy: RetryPolicy | None = None,
        limiter: RateLimiter | None = None,
        quota: DailyQuota | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float | httpx.Timeout = httpx.Timeout(
            # `read` is the gap between bytes, not the total request time, so a
            # trickling server never trips a single scalar timeout. 30s is
            # generous for one short completion.
            connect=10.0,
            read=30.0,
            write=10.0,
            pool=5.0,
        ),
    ):
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set; refusing to start "
                "(the runner never runs without explicit credentials)"
            )
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {key}"},
            timeout=timeout,
            transport=transport,
        )
        # An explicit policy pins every knob; without one the knobs stay
        # late-bound to the attributes so `client.backoff_base = 0.0` (tests)
        # and `client.max_total_seconds = budget` (scripts) keep working.
        self._policy = policy
        self.limiter = limiter or RateLimiter(None)
        self.quota = quota

    @property
    def policy(self) -> RetryPolicy:
        """The effective policy, including any attribute overrides."""
        if self._policy is not None:
            return self._policy
        return RetryPolicy(
            max_attempts=int(self.max_attempts),
            max_timeout_attempts=int(self.max_timeout_attempts),
            max_retry_after=float(self.max_retry_after),
            backoff_base=float(self.backoff_base),
            max_backoff=float(self.max_backoff),
            max_backoff_long=float(self.max_backoff_long),
            max_total_seconds=float(self.max_total_seconds),
            honor_long_retry_after=bool(self.honor_long_retry_after),
        )

    def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatReply:
        payload: dict = {
            "model": model,
            "messages": messages,
            "usage": {"include": True},
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        policy = self.policy
        last_exc: Exception | None = None
        last_reason = "unknown"
        started = time.monotonic()
        timeouts = 0
        made = 0
        for attempt in range(policy.max_attempts):
            made = attempt + 1
            wait: float | None = None
            honored_long = False
            # Before *every* POST, retries included: a retry spends the same
            # account-wide RPM budget as a first attempt, which the previous
            # code ignored — so a retry storm was itself generating 429s.
            if self.quota is not None:
                self.quota.take()
            self.limiter.acquire()
            try:
                resp = self._http.post("/chat/completions", json=payload)
            except httpx.TimeoutException as exc:
                # A slow model is a property of the model, not a runner bug:
                # retry, then surface it as a per-task outcome upstream. Far
                # fewer retries than a 429 gets, though — a rate limit clears
                # on its own, whereas a model that stalled once usually stalls
                # again, and each stall costs the full read timeout.
                last_exc, last_reason = exc, "timeout"
                timeouts += 1
                if timeouts >= policy.max_timeout_attempts:
                    break
            except httpx.HTTPError as exc:
                # Connection resets, DNS blips, protocol errors — all transient.
                last_exc, last_reason = exc, f"{type(exc).__name__}"
            else:
                if resp.status_code in RETRYABLE:
                    last_exc = httpx.HTTPStatusError(
                        f"HTTP {resp.status_code} from OpenRouter",
                        request=resp.request,
                        response=resp,
                    )
                    last_reason = f"HTTP {resp.status_code}"
                    wait = self._retry_after(resp)
                    if wait is not None and wait > policy.max_retry_after:
                        if not policy.honor_long_retry_after:
                            raise ChatFailedError(
                                f"{model}: HTTP {resp.status_code}, server asked "
                                f"for {wait:.0f}s — longer than this run will wait "
                                f"(max_retry_after={policy.max_retry_after:.0f}s; "
                                f"pass --honor-retry-after to sit through it)"
                            ) from last_exc
                        # Honored: clamp to max_backoff_long, not max_backoff,
                        # and say so — an unannounced long sleep reads as a hang.
                        wait = min(wait, policy.max_backoff_long)
                        honored_long = True
                        wake = time.strftime(
                            "%H:%M:%S", time.localtime(time.time() + wait)
                        )
                        print(
                            f"{model}: HTTP {resp.status_code}, honoring "
                            f"Retry-After — sleeping {wait:.0f}s, waking at {wake}",
                            file=sys.stderr,
                            flush=True,
                        )
                elif resp.is_error:
                    # 4xx other than 429 (bad model id, no credit, moderation):
                    # retrying cannot help, so fail this task immediately.
                    raise ChatFailedError(
                        f"{model}: HTTP {resp.status_code} from OpenRouter — "
                        f"{resp.text[:300]}"
                    )
                else:
                    try:
                        data = resp.json()
                        usage = data.get("usage") or {}
                        content = data["choices"][0]["message"]["content"]
                    except (ValueError, KeyError, IndexError, TypeError) as exc:
                        # A 200 with no choices happens on upstream provider
                        # errors; treat it as retryable rather than a crash.
                        last_exc = exc
                        last_reason = f"malformed response ({type(exc).__name__})"
                    else:
                        return ChatReply(
                            content=content or "",
                            cost=usage.get("cost"),
                            usage=usage,
                        )
            if attempt == policy.max_attempts - 1:
                break
            if wait is None:
                wait = policy.backoff_base * (2**attempt) * (0.5 + random.random())
            if not honored_long:
                wait = min(wait, policy.max_backoff)
            # Never sleep past the budget only to be cut off on waking.
            if time.monotonic() - started + wait >= policy.max_total_seconds:
                last_reason = f"{last_reason}; total time budget exhausted"
                break
            time.sleep(wait)
        raise ChatFailedError(
            f"{model}: giving up after {made} attempt(s) in "
            f"{time.monotonic() - started:.1f}s (last: {last_reason})"
        ) from last_exc

    def _retry_after(self, resp: httpx.Response) -> float | None:
        """Honor the server's own pacing when it tells us how long to wait.

        Free-tier 429s are the dominant failure here and blind exponential
        backoff undershoots them badly."""
        raw = resp.headers.get("retry-after")
        if not raw:
            return None
        try:
            return max(0.0, float(raw))
        except ValueError:
            return None
