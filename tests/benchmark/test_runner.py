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
    ChatFailedError,
    CostTracker,
    OpenRouterClient,
)
from geocase.benchmark.runner.orchestrator import plan_run, run_bare_track
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
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(500, json={"error": "boom"})

    client = _client(handler)
    client.backoff_base = 0.0
    with pytest.raises(ChatFailedError):
        client.chat("test/model", [{"role": "user", "content": "hi"}])
    assert len(calls) == client.max_attempts


def test_client_retries_timeouts_then_fails_without_crashing():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    client = _client(handler)
    client.backoff_base = 0.0
    with pytest.raises(ChatFailedError, match="timeout"):
        client.chat("test/model", [{"role": "user", "content": "hi"}])


def test_client_retries_transport_errors():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 2:
            raise httpx.ConnectError("reset", request=request)
        return _ok_response()

    client = _client(handler)
    client.backoff_base = 0.0
    assert client.chat("test/model", [{"role": "user", "content": "hi"}]).cost == 0.01


def test_client_retries_malformed_200_response():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 2:
            return httpx.Response(200, json={"error": {"message": "upstream down"}})
        return _ok_response()

    client = _client(handler)
    client.backoff_base = 0.0
    assert client.chat("test/model", [{"role": "user", "content": "hi"}]).cost == 0.01


def test_client_does_not_retry_non_retryable_4xx():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404, json={"error": "no such model"})

    client = _client(handler)
    client.backoff_base = 0.0
    with pytest.raises(ChatFailedError, match="404"):
        client.chat("test/model", [{"role": "user", "content": "hi"}])
    assert len(calls) == 1


def test_client_honors_retry_after_header(monkeypatch):
    slept = []
    monkeypatch.setattr("geocase.benchmark.runner.openrouter.time.sleep", slept.append)
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 2:
            return httpx.Response(429, headers={"retry-after": "7"})
        return _ok_response()

    _client(handler).chat("test/model", [{"role": "user", "content": "hi"}])
    assert slept == [7.0]


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


# ------------------------------------------------------- failure containment


def _geo_tasks():
    """One domain's tasks: run_bare_track refuses a mixed set (trap 12)."""
    return [t for t in all_tasks() if t.domain == "geo"]


def _bare_config():
    return {
        "defaults": {"trials": 1},
        "budget": {"max_usd_total": 1.0},
        "models": [{"id": "a/model", "label": "A", "tracks": ["bare"]}],
    }


def test_one_failing_task_does_not_stop_the_run(tmp_path, monkeypatch):
    """A 429 on one task must not abort the remaining tasks."""
    tasks = _geo_tasks()[:3]
    seen = []

    def fake_run_bare_task(client, model_id, task, **kwargs):
        seen.append(task.name)
        if task.name == tasks[1].name:
            raise ChatFailedError("a/model: giving up (last: HTTP 429)")
        from geocase.benchmark.runner.bare import BareResult

        return BareResult(task.name, "```python\nx=1\n```", "x=1", 0.0, {})

    monkeypatch.setattr(
        "geocase.benchmark.runner.bare.run_bare_task", fake_run_bare_task
    )
    monkeypatch.setattr(
        "geocase.benchmark.runner.orchestrator.grade_in_subprocess", lambda d: []
    )
    monkeypatch.setattr(
        "geocase.benchmark.runner.orchestrator.OpenRouterClient", lambda: object()
    )

    run_bare_track(_bare_config(), out_root=tmp_path, tasks=tasks)

    assert seen == [t.name for t in tasks], "run stopped early on the failing task"
    gen = next(tmp_path.glob("*_a-model_bare/generated/trial1"))
    meta = json.loads((gen / f"{tasks[1].name}.meta.json").read_text())
    assert meta["status"] == "api_failure"
    assert meta["extracted"] is False


def test_resume_retries_api_failures_but_keeps_real_results(tmp_path, monkeypatch):
    tasks = _geo_tasks()[:2]
    attempts = []
    fail_first = {tasks[1].name}

    def fake_run_bare_task(client, model_id, task, **kwargs):
        attempts.append(task.name)
        if task.name in fail_first:
            raise ChatFailedError("rate limited")
        from geocase.benchmark.runner.bare import BareResult

        return BareResult(task.name, "```python\nx=1\n```", "x=1", 0.0, {})

    monkeypatch.setattr(
        "geocase.benchmark.runner.bare.run_bare_task", fake_run_bare_task
    )
    monkeypatch.setattr(
        "geocase.benchmark.runner.orchestrator.grade_in_subprocess", lambda d: []
    )
    monkeypatch.setattr(
        "geocase.benchmark.runner.orchestrator.OpenRouterClient", lambda: object()
    )

    run_bare_track(_bare_config(), out_root=tmp_path, tasks=tasks)
    attempts.clear()
    fail_first.clear()  # the rate limit has cleared
    run_bare_track(_bare_config(), out_root=tmp_path, tasks=tasks)

    # Only the previously-failed task is retried; the good one is not re-spent.
    assert attempts == [tasks[1].name]
    gen = next(tmp_path.glob("*_a-model_bare/generated/trial1"))
    assert "status" not in json.loads((gen / f"{tasks[1].name}.meta.json").read_text())


def test_client_stops_retrying_timeouts_early():
    """A stall costs the full read timeout, so it must not be retried like a 429."""
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ReadTimeout("stalled", request=request)

    client = _client(handler)
    client.backoff_base = 0.0
    with pytest.raises(ChatFailedError):
        client.chat("test/model", [{"role": "user", "content": "hi"}])
    assert len(calls) == client.max_timeout_attempts
    assert len(calls) < client.max_attempts


def test_client_honors_a_total_time_budget(monkeypatch):
    """No combination of attempts and backoff may outlive the budget."""
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, json={"error": "rate limited"})

    client = _client(handler)
    client.backoff_base = 30.0  # each sleep would blow the budget
    client.max_total_seconds = 1.0
    slept = []
    monkeypatch.setattr("geocase.benchmark.runner.openrouter.time.sleep", slept.append)
    with pytest.raises(ChatFailedError, match="budget"):
        client.chat("test/model", [{"role": "user", "content": "hi"}])
    assert not slept, "slept past the budget instead of giving up"
    assert len(calls) == 1
