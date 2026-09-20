"""Prompt-hash stability (Plan 16 Phase 1 gate; versioned by Plan 46 §0.3).

Every committed bare run records the sha256 of the prompt it was actually sent.
Re-deriving those hashes from today's code turns "we think we did not change
the prompts" into a CI-enforced fact, and retroactively guards the committed
runs against any future prompt edit — including the {deps} slot Plan 16
introduced.

A deliberate prompt change is allowed, but it cannot happen silently and it
cannot be absorbed by repinning. Each task carries a ``prompt_version``; a
run's meta records the version it was sent (absent means 1, the version every
pre-Plan-46 run saw), and the superseded text is kept as
``tasks/<name>/prompt.v<N>.md``. So a committed hash must reproduce **from the
version that run recorded** — a run at v1 while the tree is at v2 is expected
to differ from today's prompt and is reported as such, not as a failure.
"""

import hashlib
import json
from pathlib import Path

import pytest

from geocase.benchmark.registry import all_tasks, get_task
from geocase.benchmark.runner.bare import bare_prompt

RUNS = Path(__file__).resolve().parents[2] / "results" / "runs"


def _committed_metas() -> list[Path]:
    return sorted(
        p
        for run in RUNS.glob("*_bare*")
        for p in run.glob("generated/trial*/*.meta.json")
        if "prompt_sha256" in json.loads(p.read_text())
    )


METAS = _committed_metas()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_there_are_committed_prompt_hashes_to_check():
    # Guards against the glob silently matching nothing and the whole gate
    # passing vacuously — the benchmark's own failure mode.
    assert METAS, f"no *.meta.json with a prompt_sha256 under {RUNS}"


@pytest.mark.parametrize(
    "meta_path", METAS, ids=lambda p: f"{p.parents[2].name}/{p.stem}"
)
def test_committed_prompt_hash_reproduces_from_the_version_it_recorded(meta_path):
    meta = json.loads(meta_path.read_text())
    task = get_task(meta["task"])
    recorded_version = int(meta.get("prompt_version", 1))
    assert recorded_version <= task.prompt_version, (
        f"{meta_path}: recorded prompt_version {recorded_version} is newer than "
        f"the tree's {task.prompt_version} — the task.yaml was rolled back"
    )
    got = _sha(bare_prompt(task, version=recorded_version))
    assert got == meta["prompt_sha256"], (
        f"{meta_path}: prompt v{recorded_version} for {task.name} no longer "
        f"reproduces (recorded {meta['prompt_sha256'][:12]}…, now {got[:12]}…)"
    )
    if recorded_version < task.prompt_version:
        # Expected to differ, and reported: this run was sent an older prompt
        # than the one in the tree, so its numbers are not comparable with a
        # run made today without saying so.
        current = _sha(bare_prompt(task))
        assert current != got, (
            f"{task.name}: prompt_version was bumped to {task.prompt_version} "
            f"but the prompt text is unchanged since v{recorded_version} — "
            f"a version bump must correspond to an edit"
        )
        pytest.skip(
            f"{task.name}: run recorded prompt v{recorded_version}, tree is at "
            f"v{task.prompt_version} — hash reproduces from the archived text; "
            f"do not compare this run with a v{task.prompt_version} run"
        )


@pytest.mark.parametrize(
    "task", [t for t in all_tasks() if t.prompt_version > 1], ids=lambda t: t.name
)
def test_every_superseded_prompt_version_is_archived(task):
    """A bump without the archived text would make the old hash unreproducible."""
    for version in range(1, task.prompt_version):
        archived = task.directory / f"prompt.v{version}.md"
        assert archived.is_file(), f"{task.name}: missing {archived.name}"
        assert task.prompt_template_at(version) != task.prompt_template, (
            f"{task.name}: prompt.v{version}.md is identical to prompt.md"
        )


def test_the_version_field_is_exercised():
    """Phase 0 edited two prompts; both must be at v2 with v1 archived."""
    assert {t.name for t in all_tasks() if t.prompt_version > 1} >= {
        "project_line",
        "utm_epsg_for",
    }
