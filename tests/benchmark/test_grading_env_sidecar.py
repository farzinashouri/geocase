"""Every committed run records the environment it was graded under (issue #34).

Records stay byte-identical (``module_sha256`` is provenance), so runs written
before ``run.json`` carried ``grading_env`` get a sidecar ``grading_env.json``
beside the record instead.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geocase.benchmark.runner.record import GRADING_PACKAGES

RUNS = Path(__file__).resolve().parents[2] / "results" / "runs"
RUN_DIRS = (
    sorted(p for p in RUNS.iterdir() if (p / "run.json").is_file())
    if RUNS.is_dir()
    else []
)


def _recorded(run_dir: Path) -> dict | None:
    inline = json.loads((run_dir / "run.json").read_text()).get("grading_env")
    if inline is not None:
        return inline
    sidecar = run_dir / "grading_env.json"
    if sidecar.is_file():
        return json.loads(sidecar.read_text())["grading_env"]
    return None


@pytest.mark.parametrize("run_dir", RUN_DIRS, ids=lambda p: p.name)
def test_every_run_records_its_grading_env(run_dir: Path):
    env = _recorded(run_dir)
    assert env is not None, f"{run_dir.name}: no grading_env in run.json or sidecar"
    assert "python" in env and all(p in env for p in GRADING_PACKAGES)
