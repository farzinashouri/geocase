"""Structure of `.github/workflows/agent-labels.yml`.

Closing an issue never touches its labels, and the agent triages open issues
only, so a merged PR used to leave `agent:pr-open` on its closed issue forever.
This workflow strips the agent's state labels when an issue closes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "agent-labels.yml"
AGENT_STATE_LABELS = (
    "agent:ready",
    "agent:in-progress",
    "agent:pr-open",
    "agent:needs-human",
)


@pytest.fixture(scope="module")
def wf() -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW.read_text())
    # PyYAML reads the bare key `on` as the boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return data


def test_runs_when_an_issue_closes(wf: dict[str, Any]) -> None:
    assert wf["on"] == {"issues": {"types": ["closed"]}}


def test_only_needs_issue_write(wf: dict[str, Any]) -> None:
    assert wf["permissions"] == {"issues": "write"}


def test_removes_every_agent_state_label(wf: dict[str, Any]) -> None:
    (job,) = wf["jobs"].values()
    script = "\n".join(s.get("run", "") for s in job["steps"])
    for label in AGENT_STATE_LABELS:
        assert f"--remove-label {label}" in script
