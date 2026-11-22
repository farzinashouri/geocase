"""`/merge-issue N` merges the agent's PR for issue N (#194).

Agent PRs no longer merge by themselves; the owner merges each one. The
command finds the PR, refuses unless its checks are green, merges, and does
the housekeeping CLAUDE.md asks for after every merge. These tests pin that
contract.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMAND = ROOT / ".claude" / "commands" / "merge-issue.md"


def _text() -> str:
    return COMMAND.read_text()


def test_command_exists_and_takes_an_issue_number() -> None:
    text = _text()
    assert text.startswith("---\n")
    assert "argument-hint:" in text
    assert "$ARGUMENTS" in text


def test_finds_exactly_one_pr_that_closes_the_issue() -> None:
    text = _text()
    assert "closingIssuesReferences" in text
    assert "agent/<N>-" in text
    assert "more than one" in text


def test_refuses_unless_checks_are_green() -> None:
    text = _text()
    assert "gh pr checks" in text
    assert "pending" in text and "fail" in text
    assert "isDraft" in text
    assert "mergeable" in text


def test_admin_only_for_code_owner_review() -> None:
    # Running the command is the owner's review; it never skips failed checks.
    text = _text()
    assert "gh pr merge <PR> --merge" in text
    assert "--admin" in text
    assert "Code Owner" in text
    assert "never use `--admin` to skip a failed or pending check" in text


def test_does_the_housekeeping_after_the_merge() -> None:
    text = _text()
    assert "git pull --ff-only" in text
    assert "git fetch --prune" in text
    assert "git/refs/heads/" in text  # remote branch deleted, local one kept
    assert "Depends on #<N>" in text
    assert "blocked" in text
