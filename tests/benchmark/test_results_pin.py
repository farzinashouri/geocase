"""Every committed run carries a current, honest record (Plan 17 §2.3-2.4).

Two failures this pins, both found on disk on 2026-08-11:

* ``nano-30b`` had no ``graded.json`` at all — a committed run with no verdicts.
* No bare run had a ``run.json``, so nothing recorded that
  ``super-120b``'s ``{CORRECT: 4, LOUD: 2, MISSING: 14}`` was 14 API failures
  rather than model behaviour.

Re-grading here is deliberately in-process against the *committed* modules: the
assertion is that the recorded statuses still follow from the code on disk, so a
grader change that silently moves a published number fails the build.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geocase.benchmark.cli import select_tasks
from geocase.benchmark.grading import grade_directory

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS = REPO_ROOT / "results" / "runs"


def _run_dirs() -> list[Path]:
    if not RUNS.is_dir():
        return []
    return sorted(p for p in RUNS.iterdir() if (p / "generated").is_dir())


def _trial_dirs() -> list[Path]:
    return [t for r in _run_dirs() for t in sorted((r / "generated").glob("trial*"))]


@pytest.mark.parametrize(
    "trial_dir", _trial_dirs(), ids=lambda p: f"{p.parent.parent.name}/{p.name}"
)
def test_every_committed_trial_has_a_grading(trial_dir: Path):
    assert (trial_dir / "graded.json").is_file(), (
        f"{trial_dir} has generated modules but no graded.json — a committed "
        f"run with no verdicts cannot be reported on"
    )


@pytest.mark.parametrize(
    "trial_dir", _trial_dirs(), ids=lambda p: f"{p.parent.parent.name}/{p.name}"
)
def test_committed_gradings_still_reproduce(trial_dir: Path):
    """Regrading the committed modules must return the recorded statuses."""
    recorded = {
        o["task"]: o["outcome"]
        for o in json.loads((trial_dir / "graded.json").read_text())
    }
    tasks = [t for t in select_tasks(None, None) if t.name in recorded]
    fresh = {o.task: o.outcome for o in grade_directory(trial_dir, tasks)}
    drifted = {
        name: (recorded[name], fresh[name])
        for name in recorded
        if fresh.get(name) != recorded[name]
    }
    assert not drifted, (
        f"{trial_dir}: regrading moved these outcomes {drifted} — either the "
        f"grader changed or the committed record is stale"
    )


@pytest.mark.parametrize("run_dir", _run_dirs(), ids=lambda p: p.name)
def test_every_committed_run_has_a_record(run_dir: Path):
    record_path = run_dir / "run.json"
    assert record_path.is_file(), f"{run_dir} has no run.json"
    record = json.loads(record_path.read_text())
    assert record["model"]["id"], "run.json records no model id"
    assert "integrity" in record, "run.json carries no integrity block"


@pytest.mark.parametrize("run_dir", _run_dirs(), ids=lambda p: p.name)
def test_integrity_flag_matches_the_api_failures_on_disk(run_dir: Path):
    """``publishable`` is false whenever a single api_failure is present.

    This is what stops "4 CORRECT / 14 MISSING" from ever being read as a
    model result."""
    from geocase.benchmark.runner.record import scan_integrity

    recorded = json.loads((run_dir / "run.json").read_text())["integrity"]
    fresh = scan_integrity(run_dir)
    assert recorded["api_failures"] == fresh["api_failures"]
    assert recorded["publishable"] == fresh["publishable"]
    if fresh["api_failures"]:
        assert recorded["publishable"] is False
