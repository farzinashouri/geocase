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
    max_attempts = 5
    backoff_base = 1.0  # seconds; exponential with jitter

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 300.0,
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
        for attempt in range(self.max_attempts):
            resp = self._http.post("/chat/completions", json=payload)
            if resp.status_code in RETRYABLE:
                last_exc = httpx.HTTPStatusError(
                    f"HTTP {resp.status_code} from OpenRouter",
                    request=resp.request,
                    response=resp,
                )
                time.sleep(self.backoff_base * (2**attempt) * (0.5 + random.random()))
                continue
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage") or {}
            return ChatReply(
                content=data["choices"][0]["message"]["content"],
                cost=usage.get("cost"),
                usage=usage,
            )
        assert last_exc is not None
        raise last_exc
