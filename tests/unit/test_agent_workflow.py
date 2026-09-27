"""Structure of `.github/workflows/agent.yml` (Plan 49, issue #41).

The agent runs unattended, so its rails are pinned here rather than trusted to
the prompt alone: manual trigger with a triage-only mode, no live schedule
until the dry run (#42) is reviewed, a time box, the GDAL environment the
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


def test_schedule_is_disabled_until_dry_run_reviewed(wf: dict[str, Any]) -> None:
    # #43 enables the cron after the #42 dry run.
    assert "schedule" not in wf["on"]


def test_time_boxed_and_serialised(wf: dict[str, Any]) -> None:
    assert wf["jobs"]["agent"]["timeout-minutes"] == 60
    assert wf["concurrency"]["cancel-in-progress"] is False


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
