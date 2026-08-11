"""OpenRouter chat client.

Auth comes from ``OPENROUTER_API_KEY`` only; the client refuses to start
without it, never logs it, and it must never be committed. ``usage.include``
is always requested so cost accounting is live, feeding the budget abort."""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass

import httpx

BASE_URL = "https://openrouter.ai/api/v1"
RETRYABLE = {429, 500, 502, 503, 504}


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

        last_exc: Exception | None = None
        last_reason = "unknown"
        started = time.monotonic()
        timeouts = 0
        made = 0
        for attempt in range(self.max_attempts):
            made = attempt + 1
            wait: float | None = None
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
                if timeouts >= self.max_timeout_attempts:
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
                    if wait is not None and wait > self.max_retry_after:
                        raise ChatFailedError(
                            f"{model}: HTTP {resp.status_code}, server asked "
                            f"for {wait:.0f}s — longer than this run will wait"
                        ) from last_exc
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
            if attempt == self.max_attempts - 1:
                break
            if wait is None:
                wait = self.backoff_base * (2**attempt) * (0.5 + random.random())
            wait = min(wait, self.max_backoff)
            # Never sleep past the budget only to be cut off on waking.
            if time.monotonic() - started + wait >= self.max_total_seconds:
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
