"""How the owner sees what is done and what is left (issue #149).

There is no fixed order and no calendar slot. Each phase is a GitHub milestone
with one issue per task; done means the issue is closed.
`.claude/statusline.sh` shows done/total per phase milestone, and `/next`
lists the open, unblocked issues of each phase (mvp first, all labels) that fit the time
the owner has, and recommends one. These tests
pin that contract.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".claude" / "statusline.sh"
PROMPT = ROOT / ".claude" / "commands" / "work-next-issue.md"
NEXT = ROOT / ".claude" / "commands" / "next.md"
SETTINGS = ROOT / ".claude" / "settings.json"

# Shape of `gh api repos/{owner}/{repo}/milestones`, trimmed to the fields used.
MILESTONES = [
    {
        "number": 4,
        "title": "Phase 1: Prove one outside integration",
        "open_issues": 9,
        "closed_issues": 1,
    },
    {
        "number": 3,
        "title": "Phase 0: Understand and talk",
        "open_issues": 8,
        "closed_issues": 3,
    },
    {
        "number": 5,
        "title": "Phase 2: Front door and GeoCase CI",
        "open_issues": 2,
        "closed_issues": 0,
    },
    {
        "number": 6,
        "title": "Phase 3: First paid pilot",
        "open_issues": 0,
        "closed_issues": 0,
    },
    {
        "number": 9,
        "title": "Some other milestone",
        "open_issues": 4,
        "closed_issues": 4,
    },
]

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None,
    reason="status line script needs bash and jq",
)


def _run(tmp_path: Path, milestones: list[dict[str, object]], stdin: str = "{}") -> str:
    data = tmp_path / "milestones.json"
    data.write_text(json.dumps(milestones))
    env = {
        **os.environ,
        "GEOCASE_STATUS_CACHE": str(tmp_path / "status.txt"),
        "GEOCASE_MILESTONES_FILE": str(data),
    }
    out = subprocess.run(
        ["bash", str(SCRIPT)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        check=True,
    )
    return out.stdout


def test_status_line_shows_done_over_total_per_phase(tmp_path: Path) -> None:
    out = _run(tmp_path, MILESTONES)
    assert "P0 3/11 · P1 1/10 · P2 0/2" in out


def test_status_line_skips_empty_and_non_phase_milestones(tmp_path: Path) -> None:
    out = _run(tmp_path, MILESTONES)
    assert "P3" not in out
    assert "other" not in out.lower()


def test_status_line_shows_model_name(tmp_path: Path) -> None:
    stdin = json.dumps({"model": {"display_name": "Opus 5.5"}})
    assert _run(tmp_path, MILESTONES, stdin).startswith("[Opus 5.5] ")


def test_status_line_without_milestones_still_prints(tmp_path: Path) -> None:
    out = _run(tmp_path, [])
    assert out.strip().endswith("done: run /next")


def test_status_line_is_one_short_line(tmp_path: Path) -> None:
    out = _run(tmp_path, MILESTONES)
    assert out.count("\n") <= 1
    assert len(out.strip()) <= 120


def test_project_settings_use_the_script() -> None:
    settings = json.loads(SETTINGS.read_text())
    assert settings["statusLine"]["type"] == "command"
    assert ".claude/statusline.sh" in settings["statusLine"]["command"]


def test_queue_has_no_fixed_order_for_the_owner() -> None:
    # #149: the owner picks any open task; the queue must not rank their work.
    assert "Your next 3" not in PROMPT.read_text()
    assert "Your next 3" not in NEXT.read_text()


def _queue_step() -> str:
    text = PROMPT.read_text()
    return text[text.index("**Queue.**") : text.index("**Repair.**")]


def test_queue_leaves_later_issues_out_of_waiting_on_you() -> None:
    # 2026-11-22: 19 issues no exit check needs moved to the "Later"
    # milestone so the owner sees only current work. The queue must not list
    # them again under Waiting on you; it shows a count and a link instead.
    step = _queue_step()
    assert '"Later"' in step
    assert "not listed" in step
    assert "count" in step and "link" in step


def test_next_command_lists_tasks_by_milestone_and_size() -> None:
    text = NEXT.read_text()
    assert text.startswith("---\n")
    assert "$ARGUMENTS" in text
    assert "--milestone" in text
    assert "size:" in text


def test_next_command_hides_blocked_and_shows_all_labels() -> None:
    # /next shows agent:ready and owner issues alike, with every label, and
    # hides blocked issues (it only says how many it hid).
    text = NEXT.read_text()
    assert "Drop issues labelled `blocked`" in text
    assert "blocked issues hidden" in text
    for state in ("agent:ready", "operator", "agent:needs-human"):
        assert state in text
    assert "all its labels" in text


def test_next_command_puts_mvp_first_and_caps_at_seven() -> None:
    text = NEXT.read_text()
    assert "`mvp` issues first" in text
    assert "at most 7" in text
    assert "at most 5" not in text


def test_next_command_recommends_one_issue() -> None:
    text = NEXT.read_text()
    assert "do not rank or recommend" not in text
    assert "**Recommended:**" in text


def test_next_command_orders_by_mvp_then_priority_then_size() -> None:
    text = NEXT.read_text()
    assert "Sort order: `mvp` → priority → size" in text
    assert "inside each group, smallest size first" not in text
