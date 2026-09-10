"""``ClaudeCliClient`` — the effort track's provider (Plan 45 Phase 2).

Every test here runs against a fake ``claude`` executable written into a tmp
directory and put on ``PATH``: no subscription is consumed, no network is
touched, and the envelope shapes under test are the ones the real CLI emits
under ``--output-format json``.
"""

from __future__ import annotations

import json
import os
import stat
import textwrap

import pytest

from geocase.benchmark.runner.claude_cli import EFFORT_LEVELS, ClaudeCliClient
from geocase.benchmark.runner.openrouter import ChatFailedError

# The usage shape here is the real CLI's, captured from `claude 2.1.263` on
# 2026-09-10: thinking tokens arrive nested under `output_tokens_details`,
# not at the top level. The client lifts them, because the whole effort axis
# is read off that one number and a silently-absent key reads as zero.
ENVELOPE = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "result": "```python\nx = 1\n```",
    "total_cost_usd": 0.0311,
    "usage": {
        "input_tokens": 10,
        "cache_creation_input_tokens": 3829,
        "output_tokens": 120,
        "output_tokens_details": {"thinking_tokens": 3965},
    },
    "modelUsage": {"claude-haiku-4-5": {"costBasis": "list"}},
}


def _fake_claude(tmp_path, body: str, version: str = "9.9.9 (Claude Code)"):
    """Install a fake ``claude`` on PATH and return the argv-capture path.

    ``--version`` is answered separately from ``-p``: the real CLI does, and a
    fake that returned the result envelope for both would let a broken version
    probe pass."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    argv_log = tmp_path / "argv.json"
    script = bin_dir / "claude"
    script.write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env python3
        import json, sys
        if "--version" in sys.argv[1:]:
            print({version!r})
            sys.exit(0)
        open({str(argv_log)!r}, "w").write(json.dumps(sys.argv[1:]))
        {body}
        """)
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return bin_dir, argv_log


@pytest.fixture
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _install(monkeypatch, tmp_path, body: str):
    bin_dir, argv_log = _fake_claude(tmp_path, body)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return argv_log


# ------------------------------------------------------------------ success


def test_well_formed_envelope_yields_a_chat_reply(monkeypatch, tmp_path, no_api_key):
    _install(monkeypatch, tmp_path, f"print({json.dumps(json.dumps(ENVELOPE))})")
    reply = ClaudeCliClient(effort="max").chat("claude-haiku-4-5", _msgs("hello"))
    assert reply.content == "```python\nx = 1\n```"
    # Lifted from output_tokens_details, and the nested copy is left alone.
    assert reply.usage["thinking_tokens"] == 3965
    assert reply.usage["output_tokens_details"]["thinking_tokens"] == 3965


def test_thinking_tokens_are_none_when_the_envelope_reports_none(
    monkeypatch, tmp_path, no_api_key
):
    """Absent, not zero. A model that reported nothing did not think zero."""
    envelope = {**ENVELOPE, "usage": {"input_tokens": 10, "output_tokens": 120}}
    _install(monkeypatch, tmp_path, f"print({json.dumps(json.dumps(envelope))})")
    reply = ClaudeCliClient(effort="low").chat("claude-haiku-4-5", _msgs("hi"))
    assert "thinking_tokens" not in reply.usage


def test_a_top_level_thinking_count_is_not_overwritten(
    monkeypatch, tmp_path, no_api_key
):
    """If a future CLI reports it at the top level, that wins."""
    envelope = {
        **ENVELOPE,
        "usage": {
            "thinking_tokens": 11,
            "output_tokens_details": {"thinking_tokens": 22},
        },
    }
    _install(monkeypatch, tmp_path, f"print({json.dumps(json.dumps(envelope))})")
    reply = ClaudeCliClient(effort="low").chat("claude-haiku-4-5", _msgs("hi"))
    assert reply.usage["thinking_tokens"] == 11


def test_cost_is_always_none_even_when_the_cli_reports_one(
    monkeypatch, tmp_path, no_api_key
):
    """``costBasis: list`` is not spend under a subscription (Plan 45 §2.2).

    Recording it would feed a number with no referent into the budget abort."""
    _install(monkeypatch, tmp_path, f"print({json.dumps(json.dumps(ENVELOPE))})")
    reply = ClaudeCliClient(effort="low").chat("claude-haiku-4-5", _msgs("hi"))
    assert reply.cost is None
    assert reply.usage["total_cost_usd_list"] == 0.0311


def test_invocation_carries_the_effort_and_isolation_flags(
    monkeypatch, tmp_path, no_api_key
):
    argv_log = _install(
        monkeypatch, tmp_path, f"print({json.dumps(json.dumps(ENVELOPE))})"
    )
    ClaudeCliClient(effort="xhigh").chat("claude-opus-5", _msgs("the prompt"))
    argv = json.loads(argv_log.read_text())
    assert argv[:2] == ["-p", "the prompt"]
    assert "--effort" in argv and argv[argv.index("--effort") + 1] == "xhigh"
    assert "--model" in argv and argv[argv.index("--model") + 1] == "claude-opus-5"
    assert argv[argv.index("--output-format") + 1] == "json"
    # Local settings and MCP servers must not leak into a benchmark run.
    assert "--strict-mcp-config" in argv
    assert argv[argv.index("--setting-sources") + 1] == ""


def test_multiple_messages_are_joined_into_one_prompt(
    monkeypatch, tmp_path, no_api_key
):
    argv_log = _install(
        monkeypatch, tmp_path, f"print({json.dumps(json.dumps(ENVELOPE))})"
    )
    ClaudeCliClient(effort="low").chat(
        "claude-haiku-4-5",
        [{"role": "user", "content": "one"}, {"role": "user", "content": "two"}],
    )
    assert json.loads(argv_log.read_text())[1] == "one\n\ntwo"


# ------------------------------------------------------------------ failure


def test_non_zero_exit_raises_chat_failed(monkeypatch, tmp_path, no_api_key):
    _install(monkeypatch, tmp_path, 'sys.stderr.write("boom\\n"); sys.exit(3)')
    with pytest.raises(ChatFailedError, match="exit 3"):
        ClaudeCliClient(effort="low").chat("claude-haiku-4-5", _msgs("hi"))


def test_unparseable_stdout_raises_chat_failed(monkeypatch, tmp_path, no_api_key):
    _install(monkeypatch, tmp_path, 'print("not json at all")')
    with pytest.raises(ChatFailedError):
        ClaudeCliClient(effort="low").chat("claude-haiku-4-5", _msgs("hi"))


def test_envelope_without_result_raises_chat_failed_not_keyerror(
    monkeypatch, tmp_path, no_api_key
):
    _install(monkeypatch, tmp_path, 'print(json.dumps({"type": "result"}))')
    with pytest.raises(ChatFailedError):
        ClaudeCliClient(effort="low").chat("claude-haiku-4-5", _msgs("hi"))


def test_cli_error_envelope_raises_chat_failed(monkeypatch, tmp_path, no_api_key):
    """``is_error: true`` at exit 0 is still a failed task, not an answer."""
    _install(
        monkeypatch,
        tmp_path,
        'print(json.dumps({"type": "result", "is_error": True, '
        '"result": "rate limit reached"}))',
    )
    with pytest.raises(ChatFailedError, match="rate limit"):
        ClaudeCliClient(effort="low").chat("claude-haiku-4-5", _msgs("hi"))


def test_timeout_raises_chat_failed(monkeypatch, tmp_path, no_api_key):
    _install(monkeypatch, tmp_path, "import time; time.sleep(5)")
    client = ClaudeCliClient(effort="low", timeout=0.5)
    with pytest.raises(ChatFailedError, match="timed out"):
        client.chat("claude-haiku-4-5", _msgs("hi"))


def test_missing_executable_raises_chat_failed(monkeypatch, tmp_path, no_api_key):
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(ChatFailedError, match="not on PATH"):
        ClaudeCliClient(effort="low").chat("claude-haiku-4-5", _msgs("hi"))


# ----------------------------------------------------------------- version


def test_harness_version_is_read_from_the_installed_cli(
    monkeypatch, tmp_path, no_api_key
):
    """Recorded, not assumed. The preamble is a function of the release."""
    from geocase.benchmark.runner.claude_cli import detect_cli_version

    bin_dir, _ = _fake_claude(tmp_path, "pass", version="3.0.1 (Claude Code)")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    detect_cli_version.cache_clear()
    assert detect_cli_version() == "3.0.1"


def test_harness_version_falls_back_to_unknown_not_to_a_stale_literal(
    monkeypatch, tmp_path, no_api_key
):
    """A wrong version is worse than an admitted-unknown one.

    ``harness_version`` exists so a record is reproducible; a hardcoded value
    that no longer matches the installed CLI makes it confidently wrong."""
    from geocase.benchmark.runner.claude_cli import detect_cli_version

    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    detect_cli_version.cache_clear()
    assert detect_cli_version() == "unknown"


def test_unparseable_version_output_is_unknown(monkeypatch, tmp_path, no_api_key):
    from geocase.benchmark.runner.claude_cli import detect_cli_version

    bin_dir, _ = _fake_claude(tmp_path, "pass", version="something odd")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    detect_cli_version.cache_clear()
    assert detect_cli_version() == "unknown"


# ------------------------------------------------------------------ guards


def test_refuses_to_run_with_an_api_key_present(monkeypatch, tmp_path):
    """A key on the environment means metered billing, silently (Plan 45 §2.2)."""
    _install(monkeypatch, tmp_path, f"print({json.dumps(json.dumps(ENVELOPE))})")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-whatever")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        ClaudeCliClient(effort="low")


def test_rejects_an_unknown_effort_level(no_api_key):
    with pytest.raises(ValueError, match="effort"):
        ClaudeCliClient(effort="turbo")
    assert EFFORT_LEVELS == ("low", "medium", "high", "xhigh", "max")


def test_satisfies_the_chat_client_protocol(no_api_key):
    from geocase.benchmark.runner.client import ChatClient

    assert issubclass(ClaudeCliClient, ChatClient)


def test_rate_limiter_is_consulted_before_each_call(monkeypatch, tmp_path, no_api_key):
    """Rate limits, not dollars, are the real ceiling on this track."""
    _install(monkeypatch, tmp_path, f"print({json.dumps(json.dumps(ENVELOPE))})")

    calls = []

    class SpyLimiter:
        def acquire(self):
            calls.append("acquire")

    client = ClaudeCliClient(effort="low", limiter=SpyLimiter())
    client.chat("claude-haiku-4-5", _msgs("hi"))
    client.chat("claude-haiku-4-5", _msgs("hi"))
    assert calls == ["acquire", "acquire"]


def _msgs(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]
