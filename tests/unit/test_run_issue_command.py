"""`/run-issue N` starts the development agent on one named issue (2026-11-22).

The agent has no schedule; the owner starts each run. The command checks the
issue first, so a run is not spent on an issue the agent will refuse. These
tests pin that contract.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMAND = ROOT / ".claude" / "commands" / "run-issue.md"


def _text() -> str:
    return COMMAND.read_text()


def test_command_exists_and_takes_an_issue_number() -> None:
    text = _text()
    assert text.startswith("---\n")
    assert "argument-hint:" in text
    assert "$ARGUMENTS" in text


def test_checks_the_issue_before_starting() -> None:
    # The same rule the agent's Pick step applies (work-next-issue.md).
    text = _text()
    assert "gh issue view" in text
    assert "agent:ready" in text
    assert "blocked" in text
    assert "OPEN" in text


def test_checks_the_workflow_is_enabled_and_never_enables_it() -> None:
    # A disabled workflow cannot be started. Enabling it is the owner's call.
    text = _text()
    assert "actions/workflows/agent.yml --jq .state" in text
    assert "never run `gh workflow enable`" in text


def test_warns_at_the_open_pr_limit() -> None:
    # At 3 open agent PRs the agent only triages (work-next-issue.md, Limits).
    text = _text()
    assert "agent:pr-open" in text
    assert "3" in text


def test_starts_the_agent_on_the_named_issue() -> None:
    text = _text()
    assert "gh workflow run agent.yml -f issue=" in text
    assert "gh run list --workflow agent.yml" in text
