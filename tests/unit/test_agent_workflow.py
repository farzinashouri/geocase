"""Structure of `.github/workflows/agent.yml` (Plan 49, issue #41).

The agent runs unattended, so its rails are pinned here rather than trusted to
the prompt alone: manual trigger with a triage-only mode, a weekday-night
schedule (enabled by #43 after the #42 dry run), a time box, the GDAL environment the
catalog gates need, and a tool deny list that blocks merge, tag, release and
pushes to main even if the model ignores the prompt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "agent.yml"


@pytest.fixture(scope="module")
def wf() -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW.read_text())
    # PyYAML reads the bare key `on` as the boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return data


def _steps(wf: dict[str, Any]) -> list[dict[str, Any]]:
    return wf["jobs"]["agent"]["steps"]


def _claude_step(wf: dict[str, Any]) -> dict[str, Any]:
    (step,) = [
        s
        for s in _steps(wf)
        if s.get("uses", "").startswith("anthropics/claude-code-action")
    ]
    return step


def test_manual_trigger_has_triage_only_mode(wf: dict[str, Any]) -> None:
    mode = wf["on"]["workflow_dispatch"]["inputs"]["mode"]
    assert set(mode["options"]) == {"triage", "full"}
    assert mode["default"] == "triage"


def test_runs_weekday_nights(wf: dict[str, Any]) -> None:
    # Enabled by #43 after the #42 dry run was reviewed.
    assert wf["on"]["schedule"] == [{"cron": "17 1 * * 1-5"}]


def test_scheduled_runs_use_full_mode(wf: dict[str, Any]) -> None:
    # A cron run has no inputs, so the prompt must fall back to full mode.
    assert "github.event.inputs.mode || 'full'" in _claude_step(wf)["with"]["prompt"]


def test_time_boxed_and_serialised(wf: dict[str, Any]) -> None:
    # 180, not 60: bare-track benchmark runs against rate-limited free models
    # take longer than an hour.
    assert wf["jobs"]["agent"]["timeout-minutes"] == 180
    assert wf["concurrency"]["cancel-in-progress"] is False


def test_turn_cap_fits_a_full_issue(wf: dict[str, Any]) -> None:
    # #25 took 144 turns; at 120 the action marked a finished run as failed
    # and skipped the auto-merge step.
    assert "--max-turns 250" in _claude_step(wf)["with"]["claude_args"]


def test_prompt_waits_for_background_commands() -> None:
    # Bash moves a command past 120 s to the background; a benchmark run is
    # one, and ending the turn then leaves the issue in-progress with no trace.
    prompt = (ROOT / ".claude" / "commands" / "work-next-issue.md").read_text()
    assert "moved to the background" in prompt


def test_uses_conda_env_with_gdal(wf: dict[str, Any]) -> None:
    conda = [
        s
        for s in _steps(wf)
        if s.get("uses", "").startswith("conda-incubator/setup-miniconda")
    ]
    assert conda and conda[0]["with"]["environment-file"] == "environment.yml"


def test_runs_the_committed_prompt(wf: dict[str, Any]) -> None:
    assert (ROOT / ".claude" / "commands" / "work-next-issue.md").is_file()
    assert ".claude/commands/work-next-issue.md" in _claude_step(wf)["with"]["prompt"]


@pytest.mark.parametrize(
    "denied",
    [
        "Bash(gh pr merge:*)",
        "Bash(git tag:*)",
        "Bash(gh release:*)",
        "Bash(git push origin main:*)",
    ],
)
def test_irreversible_actions_are_denied(wf: dict[str, Any], denied: str) -> None:
    assert denied in _claude_step(wf)["with"]["claude_args"]


@pytest.mark.parametrize("allowed", ["Bash(gh:*)", "Bash(git:*)", "Edit", "Write"])
def test_work_tools_are_allowed(wf: dict[str, Any], allowed: str) -> None:
    # Headless runs cannot answer a permission prompt: without an allow list
    # every gh/git call is denied and the run "succeeds" having done nothing
    # (the first #42 dry run, 4 denials in 8 turns). The deny list still wins.
    assert allowed in _claude_step(wf)["with"]["claude_args"]


@pytest.mark.parametrize(
    "allowed",
    ["Bash(python3:*)", "Bash(ls:*)", "Bash(grep:*)", "Bash(head:*)", "Bash(sed:*)"],
)
def test_shell_helpers_are_allowed(wf: dict[str, Any], allowed: str) -> None:
    # The 2026-10-01 #25 run hit 18 denials on pipes through these and spent
    # its retries past the turn cap (144 of 120).
    assert allowed in _claude_step(wf)["with"]["claude_args"]


def test_transcript_is_uploaded_even_on_failure(wf: dict[str, Any]) -> None:
    # Runs on #70 and #67 ended "success" after ~30 turns with no branch or
    # comment, and the log held no transcript to say why. Keep it as an artifact.
    claude = _claude_step(wf)
    (upload,) = [
        s for s in _steps(wf) if s.get("uses", "").startswith("actions/upload-artifact")
    ]
    assert upload["if"] == "always()"
    assert upload["with"]["path"] == (
        "${{ steps." + claude["id"] + ".outputs.execution_file }}"
    )
    assert _steps(wf).index(upload) > _steps(wf).index(claude)


def _auto_merge_step(wf: dict[str, Any]) -> dict[str, Any]:
    (step,) = [
        s for s in _steps(wf) if s.get("name") == "Enable auto-merge on agent PRs"
    ]
    return step


def test_auto_merge_runs_after_claude(wf: dict[str, Any]) -> None:
    # The model stays denied `gh pr merge`; a fixed step turns on GitHub
    # auto-merge instead, so a PR merges only once the required checks pass.
    steps = _steps(wf)
    assert steps.index(_auto_merge_step(wf)) > steps.index(_claude_step(wf))


def test_auto_merge_only_touches_agent_branches(wf: dict[str, Any]) -> None:
    run = _auto_merge_step(wf)["run"]
    assert 'startswith("agent/")' in run
    assert "gh pr merge" in run and "--auto" in run
    assert "--admin" not in run  # never bypass the required checks
