"""Runner unit tests (Plan 15 Phase 4, stripped): code-block extraction,
budget abort, environment scrubbing, dry-run planning, and retry — all against
a mocked transport; nothing here spends money or touches the network."""

import json

import httpx
import pytest

from geocase.benchmark.registry import all_tasks
from geocase.benchmark.runner.extract import extract_code_block
from geocase.benchmark.runner.openrouter import (
    BudgetExceededError,
    CostTracker,
    OpenRouterClient,
)
from geocase.benchmark.runner.orchestrator import plan_run
from geocase.benchmark.runner.sandbox import scrubbed_env

# ---------------------------------------------------------------- extract


def test_extract_python_fence():
    text = "Here you go:\n```python\nx = 1\n```\nDone."
    assert extract_code_block(text) == "x = 1"


def test_extract_py_fence_and_bare_fence():
    assert extract_code_block("```py\ny = 2\n```") == "y = 2"
    assert extract_code_block("```\nz = 3\n```") == "z = 3"


def test_extract_takes_last_block():
    text = "```python\ndraft = True\n```\nActually:\n```python\nfinal = True\n```"
    assert extract_code_block(text) == "final = True"


def test_extract_unclosed_fence_is_tolerated():
    assert extract_code_block("```python\nx = 1\n") == "x = 1"


def test_extract_no_block_returns_none():
    assert extract_code_block("I cannot write code today.") is None


# ---------------------------------------------------------------- budget


def test_cost_tracker_aborts_over_budget():
    tracker = CostTracker(max_usd=1.0)
    tracker.add(0.4)
    tracker.add(0.5)
    with pytest.raises(BudgetExceededError):
        tracker.add(0.2)
    assert tracker.spent == pytest.approx(0.9)


def test_cost_tracker_unlimited_when_none():
    tracker = CostTracker(max_usd=None)
    tracker.add(1000.0)
    assert tracker.spent == 1000.0


# ---------------------------------------------------------------- sandbox env


def test_scrubbed_env_drops_secrets():
    env = scrubbed_env(
        {"PATH": "/bin", "OPENROUTER_API_KEY": "sk-x", "GH_TOKEN": "t", "HOME": "/h"}
    )
    assert env["PATH"] == "/bin"
    assert env["HOME"] == "/h"
    assert "OPENROUTER_API_KEY" not in env
    assert "GH_TOKEN" not in env


# ---------------------------------------------------------------- client


def _client(handler):
    return OpenRouterClient(api_key="test-key", transport=httpx.MockTransport(handler))


def _ok_response(content="```python\nx = 1\n```", cost=0.01):
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {"cost": cost, "prompt_tokens": 10, "completion_tokens": 5},
        },
    )


def test_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OpenRouterClient()


def test_client_chat_returns_content_and_usage():
    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "test/model"
        assert body["usage"] == {"include": True}
        assert request.headers["Authorization"] == "Bearer test-key"
        return _ok_response()

    reply = _client(handler).chat("test/model", [{"role": "user", "content": "hi"}])
    assert reply.content == "```python\nx = 1\n```"
    assert reply.cost == pytest.approx(0.01)


def test_client_retries_on_429_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, json={"error": "rate limited"})
        return _ok_response()

    client = _client(handler)
    client.backoff_base = 0.0  # no sleeping in tests
    reply = client.chat("test/model", [{"role": "user", "content": "hi"}])
    assert len(calls) == 3
    assert reply.cost == pytest.approx(0.01)


def test_client_gives_up_after_max_attempts():
    def handler(request):
        return httpx.Response(500, json={"error": "boom"})

    client = _client(handler)
    client.backoff_base = 0.0
    with pytest.raises(httpx.HTTPStatusError):
        client.chat("test/model", [{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------- dry run


def test_plan_run_counts_calls_without_spending():
    config = {
        "defaults": {"trials": 2, "temperature": 0.2},
        "budget": {"max_usd_total": 5.0},
        "models": [
            {"id": "a/free", "label": "A", "tracks": ["bare"]},
            {"id": "b/paid", "label": "B", "tracks": ["bare"]},
        ],
    }
    plan = plan_run(config, track="bare")
    n_tasks = len(all_tasks())
    assert plan.calls == 2 * 2 * n_tasks
    assert plan.budget_ceiling_usd == 5.0
