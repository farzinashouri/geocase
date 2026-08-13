"""``run.json`` for bare-track runs (Plan 17 §2.3).

``manual ingest`` has always written a run record; ``run_bare_track`` never
did, so no bare run carried a run-level record of its model, cost, or
integrity. The consequence is on disk today:
``2026-08-10_nvidia-nemotron-3-super-120b-a12b-free_bare`` grades
``{CORRECT: 4, LOUD: 2, MISSING: 14}`` where the 14 MISSING are ``api_failure``
metas, not model behaviour. Read naively that is "20% correct"; on what
actually landed it is 67%. Neither is publishable and nothing on disk said so.

The record shape is ``manual``'s verbatim (``schema_version: 2``) so one
reporting path serves both tracks, plus an ``integrity`` block:

    "integrity": {"tasks_attempted": 20, "api_failures": 14,
                  "publishable": false}

``publishable`` is false whenever a single ``api_failure`` is present. Rate
limits are not model behaviour, and a rate is not a rate if part of its
denominator never reached the model.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from geocase.benchmark.taxonomy import TrialOutcome

RUNNER_VERSION = "2.0.0.dev0"


def _slug(model_id: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", model_id.lower())


def _sha256_file(path: Path) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def scan_integrity(run_dir: Path) -> dict[str, Any]:
    """Count attempted tasks and API failures across every ``trial*/`` on disk.

    Read from the ``*.meta.json`` files rather than from a counter held in
    memory, so the record stays truthful for a resumed run and can be
    backfilled for runs that predate this module.
    """
    attempted = 0
    failures = 0
    by_trial: dict[str, dict[str, int]] = {}
    gen_root = run_dir / "generated"
    for trial_dir in sorted(gen_root.glob("trial*")) if gen_root.is_dir() else []:
        t_attempted = t_failed = 0
        for meta_path in sorted(trial_dir.glob("*.meta.json")):
            try:
                meta = json.loads(meta_path.read_text())
            except (OSError, ValueError):
                continue
            t_attempted += 1
            if meta.get("status") in ("api_failure", "timeout"):
                t_failed += 1
        attempted += t_attempted
        failures += t_failed
        by_trial[trial_dir.name] = {
            "tasks_attempted": t_attempted,
            "api_failures": t_failed,
        }
    return {
        "tasks_attempted": attempted,
        "api_failures": failures,
        "publishable": attempted > 0 and failures == 0,
        "by_trial": by_trial,
    }


def _prompt_hashes(run_dir: Path) -> dict[str, str]:
    """Prompt hashes recorded per task at run time, collected across trials."""
    hashes: dict[str, str] = {}
    gen_root = run_dir / "generated"
    for meta_path in sorted(gen_root.glob("trial*/*.meta.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        sha = meta.get("prompt_sha256")
        if sha:
            hashes.setdefault(meta.get("task", meta_path.stem), sha)
    return hashes


def _task_entries(
    run_dir: Path, outcomes_by_trial: dict[int, list[TrialOutcome]]
) -> dict[str, Any]:
    tasks: dict[str, Any] = {}
    for trial, outcomes in sorted(outcomes_by_trial.items()):
        gen_dir = run_dir / "generated" / f"trial{trial}"
        for outcome in outcomes:
            meta_path = gen_dir / f"{outcome.task}.meta.json"
            try:
                meta = json.loads(meta_path.read_text())
            except (OSError, ValueError):
                meta = {}
            module_rel = f"generated/trial{trial}/{outcome.task}.py"
            entry = {
                "trial": trial,
                "module": module_rel if (run_dir / module_rel).is_file() else None,
                "module_sha256": _sha256_file(run_dir / module_rel),
                "outcome": outcome.outcome,
                "checks": [
                    {
                        "check": c.check,
                        "kind": c.kind.value if c.kind else None,
                        "status": c.status.value,
                        "detail": c.detail,
                    }
                    for c in outcome.checks
                ],
                "turns": None,  # bare track is single-completion by definition
                "usage": meta.get("usage") or None,
                # Carried onto the task so a MISSING caused by a 429 is
                # distinguishable from a model that returned nothing.
                "status": meta.get("status"),
            }
            trials = tasks.setdefault(outcome.task, {"trials": []})["trials"]
            trials[:] = [t for t in trials if t["trial"] != trial] + [entry]
            trials.sort(key=lambda t: t["trial"])
    return tasks


def write_bare_record(
    run_dir: Path,
    *,
    model: dict,
    trials: int,
    date: str,
    config: dict,
    outcomes_by_trial: dict[int, list[TrialOutcome]],
    cost_usd: float | None,
    domain: str = "geo",
) -> dict[str, Any]:
    """Write ``run_dir/run.json`` for a bare run and return the record."""
    run_dir = Path(run_dir)
    defaults = config.get("defaults", {})
    integrity = scan_integrity(run_dir)
    record: dict[str, Any] = {
        "schema_version": 2,
        "run_id": run_dir.name,
        "date": date,
        "domain": domain,
        "model": {
            "id": model["id"],
            "label": model.get("label") or model["id"],
            "provider": "openrouter",
        },
        "track": "bare",
        "protocol": "openrouter-chat",
        "runner": {"name": "geocase-benchmark", "version": RUNNER_VERSION},
        "config": {
            "trials": trials,
            "temperature": defaults.get("temperature"),
            # Bare is a single completion with no tools: there is no turn
            # budget and no sandbox, and recording zeros would imply otherwise.
            "max_turns": None,
            "variant_seed": None,
            "sandbox_requirements_sha256": None,
            "prompt_sha256": _prompt_hashes(run_dir),
        },
        "cost_usd": cost_usd,
        "integrity": integrity,
        "tasks": _task_entries(run_dir, outcomes_by_trial),
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps(record, indent=2))
    return record


def backfill_bare_record(
    run_dir: Path, *, model_id: str | None = None, label: str | None = None
) -> dict[str, Any]:
    """Rebuild a bare ``run.json`` from what is on disk, for existing runs.

    Outcomes come from each trial's committed ``graded.json`` rather than by
    re-grading: the point is to record what those runs already report, not to
    silently restate it.
    """
    run_dir = Path(run_dir)
    metas = sorted((run_dir / "generated").glob("trial*/*.meta.json"))
    first: dict[str, Any] = {}
    for meta_path in metas:
        try:
            first = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        if first.get("model"):
            break
    resolved = model_id or first.get("model")
    if not resolved:
        raise ValueError(
            f"{run_dir}: no model id in any meta.json and none passed; "
            f"refusing to guess it from the directory name"
        )

    outcomes_by_trial: dict[int, list[TrialOutcome]] = {}
    for graded_path in sorted((run_dir / "generated").glob("trial*/graded.json")):
        trial = int(graded_path.parent.name.removeprefix("trial"))
        raw = json.loads(graded_path.read_text())
        outcomes_by_trial[trial] = [TrialOutcome.model_validate(o) for o in raw]

    # Sum only what was actually charged; a task with no cost recorded (a
    # failure, or a free model) contributes nothing rather than being guessed.
    costs = []
    for meta_path in metas:
        try:
            cost = json.loads(meta_path.read_text()).get("cost_usd")
        except (OSError, ValueError):
            continue
        if isinstance(cost, (int, float)):
            costs.append(float(cost))
    date = run_dir.name.split("_", 1)[0]

    return write_bare_record(
        run_dir,
        model={"id": resolved, "label": label or first.get("label") or resolved},
        trials=max(outcomes_by_trial or [1]),
        date=date,
        config={"defaults": {"temperature": None}},
        outcomes_by_trial=outcomes_by_trial,
        cost_usd=sum(costs) if costs else None,
    )
