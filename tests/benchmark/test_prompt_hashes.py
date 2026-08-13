"""Prompt-hash stability (Plan 16 Phase 1 gate).

Every committed bare run records the sha256 of the prompt it was actually sent.
Re-deriving those hashes from today's code turns "we think we did not change
the prompts" into a CI-enforced fact, and retroactively guards the committed
runs against any future prompt edit — including the {deps} slot this phase
introduced.

A deliberate prompt change is allowed to break this test; it just cannot happen
silently, and the runs generated under the old prompt must then be re-run or
explicitly annotated rather than quietly compared against new ones.
"""

import hashlib
import json
from pathlib import Path

import pytest

from geocase.benchmark.registry import get_task
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


def test_there_are_committed_prompt_hashes_to_check():
    # Guards against the glob silently matching nothing and the whole gate
    # passing vacuously — the benchmark's own failure mode.
    assert METAS, f"no *.meta.json with a prompt_sha256 under {RUNS}"


@pytest.mark.parametrize(
    "meta_path", METAS, ids=lambda p: f"{p.parents[2].name}/{p.stem}"
)
def test_committed_prompt_hash_still_reproduces(meta_path):
    meta = json.loads(meta_path.read_text())
    task = get_task(meta["task"])
    got = hashlib.sha256(bare_prompt(task).encode()).hexdigest()
    assert got == meta["prompt_sha256"], (
        f"{meta_path}: prompt for {task.name} has changed since this run "
        f"(recorded {meta['prompt_sha256'][:12]}…, now {got[:12]}…)"
    )
