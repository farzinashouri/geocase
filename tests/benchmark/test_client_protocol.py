"""The runner's client seam is a Protocol, not a concrete class (Plan 45 §1).

``run_bare_task`` touches its client through exactly one call — ``chat()`` —
and everything downstream consumes ``BareResult``. Pinning that as a Protocol
is what lets a second provider (Plan 45's ``claude-cli``) reach the same runner
without the bare path importing it, or knowing it exists.
"""

from __future__ import annotations

from geocase.benchmark.registry import all_tasks
from geocase.benchmark.runner.bare import run_bare_task
from geocase.benchmark.runner.client import ChatClient, ChatReply


class StubClient:
    """Implements ``chat()`` and nothing else — the whole of the seam."""

    def __init__(self, content: str = "```python\nx = 1\n```"):
        self.content = content
        self.calls: list[tuple] = []

    def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatReply:
        self.calls.append((model, messages, temperature, max_tokens))
        return ChatReply(content=self.content, cost=None, usage={"total_tokens": 7})


def test_stub_satisfies_the_protocol():
    assert isinstance(StubClient(), ChatClient)


def test_openrouter_client_satisfies_the_protocol():
    from geocase.benchmark.runner.openrouter import OpenRouterClient

    # Structural, so no instance and no credentials are needed.
    assert issubclass(OpenRouterClient, ChatClient)


def test_run_bare_task_accepts_any_chat_client():
    task = all_tasks()[0]
    client = StubClient()
    result = run_bare_task(client, "stub/model", task, temperature=0.2)
    assert result.task == task.name
    assert result.code == "x = 1"
    assert result.cost is None
    assert result.usage == {"total_tokens": 7}
    model, messages, temperature, max_tokens = client.calls[0]
    assert model == "stub/model"
    assert messages[0]["role"] == "user"
    assert temperature == 0.2
    assert max_tokens is None


def test_chat_reply_is_the_same_object_as_openrouters():
    """``runner.openrouter`` re-exports it, so old imports stay valid."""
    from geocase.benchmark.runner.openrouter import ChatReply as ORChatReply

    assert ORChatReply is ChatReply
