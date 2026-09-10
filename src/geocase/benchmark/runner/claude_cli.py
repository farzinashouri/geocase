"""The effort track's provider: ``claude -p`` as a :class:`ChatClient`.

Plan 45. This is **not** a bare-completion client and must never be read as
one. Every invocation of ``claude -p`` carries the Claude Code harness
preamble — roughly 23 800 tokens on the measured CLI, which no flag removes:
``--system-prompt`` replaces the *task* system prompt but not the harness, and
disabling every tool made the payload larger, not smaller. So a run through
this client is a Claude Code run that happens to contain the task prompt, and
``prompt_sha256`` no longer describes what the model saw in isolation. Records
written from it carry ``preamble: "claude-code-harness"`` for exactly that
reason (see :mod:`geocase.benchmark.runner.record`).

What it buys instead is ``--effort``: on one prompt and one model, ``low``
spent 46 thinking tokens and ``max`` spent 3 965. That is the experiment this
client exists to run.

Two guards are load-bearing:

* **``cost`` is always ``None``.** ``modelUsage`` reports ``costBasis: list``;
  under a subscription those dollars are never billed. Feeding them to
  ``CostTracker`` would abort a run against a number with no referent. The
  list figure is kept under ``usage.total_cost_usd_list`` — visible, clearly
  labelled, and out of the budget path.
* **``ANTHROPIC_API_KEY`` must be absent.** With a key set the same command
  falls through to metered billing without saying so.
"""

from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
from typing import Protocol

from geocase.benchmark.runner.client import ChatReply
from geocase.benchmark.runner.limiter import RateLimiter
from geocase.benchmark.runner.openrouter import ChatFailedError

EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

# Generous on purpose. The 30s read timeout that suits one OpenRouter
# completion is far too tight for ~4 000 thinking tokens at `max`.
DEFAULT_TIMEOUT_S = 600.0


@functools.cache
def detect_cli_version(executable: str = "claude") -> str:
    """The installed CLI's version, or ``"unknown"``.

    Read rather than hardcoded, because ``harness_version`` exists precisely
    so an effort record is reproducible: the preamble is a function of the
    release, and a literal that no longer matches the CLI on PATH makes the
    record confidently wrong instead of merely silent. An unreadable version
    reports ``"unknown"`` for the same reason — an admitted gap beats a stale
    number that reads as measured.

    Cached: it is one subprocess per process, not one per task in a 420-call
    sweep. ``cache_clear()`` is available to tests.
    """
    if shutil.which(executable) is None:
        return "unknown"
    try:
        proc = subprocess.run(  # noqa: S603 - argv list, no shell
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if proc.returncode != 0:
        return "unknown"
    match = re.search(r"\d+\.\d+\.\d+", proc.stdout)
    return match.group(0) if match else "unknown"


class _Limiter(Protocol):
    def acquire(self) -> object: ...


class _Quota(Protocol):
    def take(self, n: int = 1) -> None: ...


class ClaudeCliClient:
    """One ``claude -p`` invocation per :meth:`chat` call."""

    def __init__(
        self,
        *,
        effort: str,
        executable: str = "claude",
        timeout: float = DEFAULT_TIMEOUT_S,
        limiter: _Limiter | None = None,
        quota: _Quota | None = None,
    ):
        if effort not in EFFORT_LEVELS:
            raise ValueError(
                f"unknown effort {effort!r}; expected one of {', '.join(EFFORT_LEVELS)}"
            )
        if os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is set; refusing to start the claude-cli "
                "client. This track runs on a subscription seat — with a key "
                "present the same command bills per token instead, silently. "
                "Unset it for this run."
            )
        self.effort = effort
        self.executable = executable
        self.timeout = timeout
        self.limiter = limiter or RateLimiter(None)
        self.quota = quota

    def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatReply:
        # temperature/max_tokens are part of the seam but the CLI exposes
        # neither; ignoring them silently would misreport the run, so the
        # config's own `temperature: null` is what makes an effort config
        # honest (see configs/models-claude-effort.yaml).
        prompt = "\n\n".join(
            str(m.get("content", "")) for m in messages if m.get("content")
        )
        argv = [
            self.executable,
            "-p",
            prompt,
            "--model",
            model,
            "--effort",
            self.effort,
            "--output-format",
            "json",
            # No MCP servers, no user/project settings: a benchmark run must
            # not vary with whatever the operator has configured locally.
            "--strict-mcp-config",
            "--setting-sources",
            "",
        ]
        if shutil.which(self.executable) is None:
            raise ChatFailedError(
                f"{self.executable!r} is not on PATH — the effort track needs "
                f"the Claude Code CLI installed and signed in"
            )
        if self.quota is not None:
            self.quota.take()
        self.limiter.acquire()
        try:
            proc = subprocess.run(  # noqa: S603 - argv list, no shell
                argv,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ChatFailedError(
                f"{model} at effort {self.effort}: timed out after {self.timeout:.0f}s"
            ) from exc
        except OSError as exc:
            raise ChatFailedError(
                f"{model} at effort {self.effort}: could not run "
                f"{self.executable!r} ({exc})"
            ) from exc
        if proc.returncode != 0:
            raise ChatFailedError(
                f"{model} at effort {self.effort}: claude exit "
                f"{proc.returncode} — {(proc.stderr or proc.stdout)[:300]}"
            )
        return self._parse(proc.stdout, model)

    def _parse(self, stdout: str, model: str) -> ChatReply:
        """Envelope → :class:`ChatReply`. Never raises ``KeyError`` upward.

        Anything unexpected becomes ``ChatFailedError``, which the
        orchestrator already records as a per-task failure — one bad task must
        not kill a 420-call run."""
        try:
            data = json.loads(stdout)
        except ValueError as exc:
            raise ChatFailedError(
                f"{model} at effort {self.effort}: claude returned "
                f"unparseable stdout — {stdout[:300]!r}"
            ) from exc
        if not isinstance(data, dict):
            raise ChatFailedError(
                f"{model} at effort {self.effort}: expected a JSON object, "
                f"got {type(data).__name__}"
            )
        if data.get("is_error"):
            raise ChatFailedError(
                f"{model} at effort {self.effort}: claude reported an error — "
                f"{str(data.get('result') or data.get('subtype'))[:300]}"
            )
        result = data.get("result")
        if not isinstance(result, str):
            raise ChatFailedError(
                f"{model} at effort {self.effort}: envelope carries no "
                f"'result' string (keys: {sorted(data)})"
            )
        usage = dict(data.get("usage") or {})
        usage["effort"] = self.effort
        # The whole effort axis is read off this one number, and on
        # `claude 2.1.263` it arrives nested — so a reader looking for
        # `usage["thinking_tokens"]` finds nothing and takes it for zero.
        # Lifted, never overwritten: if a later CLI reports it at the top
        # level, that value is the authoritative one. Absent stays absent —
        # a model that reported no count did not think zero tokens.
        if "thinking_tokens" not in usage:
            details = usage.get("output_tokens_details")
            if isinstance(details, dict) and "thinking_tokens" in details:
                usage["thinking_tokens"] = details["thinking_tokens"]
        cost = data.get("total_cost_usd")
        if isinstance(cost, (int, float)):
            # Kept under a name that says what it is. `cost` stays None so it
            # can never reach CostTracker.
            usage["total_cost_usd_list"] = float(cost)
        return ChatReply(content=result, cost=None, usage=usage)
