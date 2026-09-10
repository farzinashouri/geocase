"""The runner's client seam (Plan 45 Phase 1).

``run_bare_task`` reaches its client through exactly one call, and everything
downstream consumes :class:`~geocase.benchmark.runner.bare.BareResult` and
never sees the client at all. The only thing that ever tied the runner to
OpenRouter was the type annotation naming the concrete class, so the seam is
declared here as a Protocol and the concrete clients merely satisfy it.

:class:`ChatReply` lives here rather than in ``openrouter`` for the same
reason — a second provider must not have to import the first to return a
reply. ``runner.openrouter`` re-exports it, so every existing import resolves
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class ChatReply:
    content: str
    # ``None`` means "no spend figure exists", not "free". A subscription-based
    # provider reports list prices that are never billed; recording those would
    # put fiction into the budget abort (Plan 45 §2.2).
    cost: float | None
    usage: dict


@runtime_checkable
class ChatClient(Protocol):
    """One single-shot completion. The whole of what the bare runner needs."""

    def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatReply: ...
