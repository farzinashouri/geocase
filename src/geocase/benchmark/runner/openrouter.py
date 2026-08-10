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
    max_attempts = 2
    backoff_base = 2.0  # seconds; exponential with jitter
    max_backoff = 60.0  # cap per sleep, incl. a server-supplied Retry-After

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60.0,
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
        for attempt in range(self.max_attempts):
            wait: float | None = None
            try:
                resp = self._http.post("/chat/completions", json=payload)
            except httpx.TimeoutException as exc:
                # A slow model is a property of the model, not a runner bug:
                # retry, then surface it as a per-task outcome upstream.
                last_exc, last_reason = exc, "timeout"
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
            time.sleep(min(wait, self.max_backoff))
        raise ChatFailedError(
            f"{model}: giving up after {self.max_attempts} attempts "
            f"(last: {last_reason})"
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
