"""Structure of `.github/workflows/release.yml` (Plan 50, issue #53).

The pipeline has one human step: approving the PyPI upload. These tests pin
what makes that step safe — PyPI waits for the TestPyPI smoke test, only the
publish jobs can mint an upload token, and a push to main tags the release
inside the same run (a tag pushed with GITHUB_TOKEN starts no workflow).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "release.yml"


@pytest.fixture(scope="module")
def wf() -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW.read_text())
    # PyYAML reads the bare key `on` as the boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return data


def _needs(job: dict[str, Any]) -> list[str]:
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else needs


def test_triggers_include_main_tags_and_manual(wf: dict[str, Any]) -> None:
    on = wf["on"]
    assert on["push"]["branches"] == ["main"]
    assert on["push"]["tags"]
    assert "workflow_dispatch" in on


def test_pipeline_order(wf: dict[str, Any]) -> None:
    jobs = wf["jobs"]
    assert "tag" in _needs(jobs["build"])
    assert "build" in _needs(jobs["publish-testpypi"])
    assert "publish-testpypi" in _needs(jobs["smoke-testpypi"])
    assert "smoke-testpypi" in _needs(jobs["publish-pypi"])
    assert "publish-pypi" in _needs(jobs["smoke-pypi"])
    assert "smoke-pypi" in _needs(jobs["github-release"])


def test_pypi_upload_is_behind_the_pypi_environment(wf: dict[str, Any]) -> None:
    assert wf["jobs"]["publish-pypi"]["environment"] == "pypi"
    assert wf["jobs"]["publish-testpypi"]["environment"] == "testpypi"


def test_only_publish_jobs_can_mint_upload_tokens(wf: dict[str, Any]) -> None:
    minting = {
        name
        for name, job in wf["jobs"].items()
        if job.get("permissions", {}).get("id-token") == "write"
    }
    assert minting == {"publish-testpypi", "publish-pypi"}
    assert wf["permissions"] == {"contents": "read"}


def test_testpypi_upload_skips_existing(wf: dict[str, Any]) -> None:
    steps = wf["jobs"]["publish-testpypi"]["steps"]
    publish = [s for s in steps if "gh-action-pypi-publish" in s.get("uses", "")]
    assert publish and publish[0]["with"]["skip-existing"] is True


@pytest.mark.parametrize("job", ["smoke-testpypi", "smoke-pypi"])
def test_smoke_jobs_cover_core_and_array(wf: dict[str, Any], job: str) -> None:
    matrix = wf["jobs"][job]["strategy"]["matrix"]
    assert sorted(matrix["mode"]) == ["array", "core"]
    text = yaml.safe_dump(wf["jobs"][job]["steps"])
    assert "smoke_release.py" in text


def test_push_to_main_waits_for_green_ci(wf: dict[str, Any]) -> None:
    # Release runs in parallel with CI on the same push; without this gate a
    # red merge commit would still be tagged and uploaded to TestPyPI (#92).
    jobs = wf["jobs"]
    gate = jobs["ci-green"]
    assert "ci-green" in _needs(jobs["tag"])
    # Only a branch push is gated; a hand-pushed tag and manual runs are not.
    assert "refs/heads/" in gate["if"] or "branch" in gate["if"]
    text = yaml.safe_dump(gate["steps"])
    assert "ci.yml" in text and "github.sha" in text.replace("GITHUB_SHA", "github.sha")
    assert "success" in text
    # The tag job still runs when the gate is skipped, but never when it failed.
    cond = jobs["tag"]["if"]
    assert "ci-green.result" in cond
    assert "failure" not in cond.replace("!= 'failure'", "")


# --- prepare-release.yml (issue #54) ---------------------------------------

WORKFLOWS = WORKFLOW.parent


def _load(name: str) -> dict[str, Any]:
    data = yaml.safe_load((WORKFLOWS / name).read_text())
    data["on"] = data.pop(True, data.get("on"))
    return data


def test_prepare_release_takes_a_version_and_opens_a_pr() -> None:
    wf = _load("prepare-release.yml")
    assert wf["on"]["workflow_dispatch"]["inputs"]["version"]["required"] is True
    text = yaml.safe_dump(wf["jobs"])
    for needed in (
        "prepare_release.py",
        "generate_changelog_page.py",
        "gh pr create",
        "gh workflow run ci.yml",
    ):
        assert needed in text, needed


def test_ci_can_be_started_by_hand() -> None:
    # A PR opened with GITHUB_TOKEN gets no checks; prepare-release.yml starts
    # CI on the release branch with `gh workflow run`, which needs this trigger.
    assert "workflow_dispatch" in _load("ci.yml")["on"]
