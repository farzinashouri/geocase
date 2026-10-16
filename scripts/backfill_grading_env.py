"""Re-grade committed runs in this environment and write ``grading_env.json`` sidecars.

Issue #34. Records under ``results/runs`` stay byte-identical (their
``module_sha256`` is provenance), so the environment goes beside them. No model
calls: it re-grades the committed generated modules. Where a fresh outcome
differs from the recorded one, both are written and the run is reported so
``CHANGELOG.md`` can name it.

    python scripts/backfill_grading_env.py [--write]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from geocase.benchmark.cli import select_tasks
from geocase.benchmark.grading import grade_directory
from geocase.benchmark.runner.record import grading_env
from geocase.benchmark.taxonomy import aggregate_outcome

RUNS = Path(__file__).resolve().parents[1] / "results" / "runs"


def _drift(trial_dir: Path) -> dict[str, dict[str, str]]:
    recorded = {
        o["task"]: o for o in json.loads((trial_dir / "graded.json").read_text())
    }
    tasks = [t for t in select_tasks(None, None) if t.name in recorded]
    out = {}
    for fresh in grade_directory(trial_dir, tasks):
        known = {c["check"] for c in recorded[fresh.task]["checks"]}
        seen = [c for c in fresh.checks if c.check in known]
        outcome = aggregate_outcome(seen) if seen else fresh.outcome
        if outcome != recorded[fresh.task]["outcome"]:
            out[fresh.task] = {
                "recorded": recorded[fresh.task]["outcome"],
                "regraded": outcome,
            }
    return out


def main() -> int:
    write = "--write" in sys.argv
    env = grading_env()
    for run_dir in sorted(RUNS.iterdir()):
        run_json = run_dir / "run.json"
        if not run_json.is_file() or "grading_env" in json.loads(run_json.read_text()):
            continue
        drift = {
            f"{t.name}/{task}": d
            for t in sorted((run_dir / "generated").glob("trial*"))
            for task, d in _drift(t).items()
        }
        sidecar = {"grading_env": env, "regrade_differs": drift}
        print(f"{run_dir.name}: {'DIFFERS ' + json.dumps(drift) if drift else 'same'}")
        if write:
            (run_dir / "grading_env.json").write_text(
                json.dumps(sidecar, indent=2) + "\n"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
