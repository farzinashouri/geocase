"""Minimal bare-track orchestrator (Plan 15 Phase 4, stripped).

``python -m geocase.benchmark run --config configs/models.yaml --track bare
--trials 3 --out results/runs/`` — incremental per-trial state (a crash does
not re-spend; existing modules are skipped), grading through a subprocess so
model code never runs in this process, ``--dry-run`` prints the call count and
cost ceiling without spending anything."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml

from geocase.benchmark.grading import grade_in_subprocess
from geocase.benchmark.registry import TaskMeta, all_tasks
from geocase.benchmark.runner.openrouter import (
    BudgetExceededError,
    CostTracker,
    OpenRouterClient,
)
from geocase.benchmark.taxonomy import TrialOutcome


@dataclass
class RunPlan:
    calls: int
    models: list[str]
    trials: int
    budget_ceiling_usd: float | None


def _models_for_track(config: dict, track: str) -> list[dict]:
    return [m for m in config.get("models", []) if track in m.get("tracks", [])]


def plan_run(config: dict, *, track: str) -> RunPlan:
    models = _models_for_track(config, track)
    trials = int(config.get("defaults", {}).get("trials", 1))
    n_tasks = len(all_tasks())
    return RunPlan(
        calls=len(models) * trials * n_tasks,
        models=[m["id"] for m in models],
        trials=trials,
        budget_ceiling_usd=config.get("budget", {}).get("max_usd_total"),
    )


def _slug(model_id: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", model_id.lower())


def run_bare_track(
    config: dict,
    *,
    out_root: Path,
    tasks: list[TaskMeta] | None = None,
    resume: bool = True,
) -> None:
    # Imported here so --dry-run and the unit tests never need credentials.
    from geocase.benchmark.runner.bare import run_bare_task

    tasks = tasks or all_tasks()
    defaults = config.get("defaults", {})
    trials = int(defaults.get("trials", 1))
    temperature = defaults.get("temperature")
    tracker = CostTracker(config.get("budget", {}).get("max_usd_total"))
    client = OpenRouterClient()
    date = dt.date.today().isoformat()

    for model in _models_for_track(config, "bare"):
        run_dir = out_root / f"{date}_{_slug(model['id'])}_bare"
        for trial in range(1, trials + 1):
            gen_dir = run_dir / "generated" / f"trial{trial}"
            gen_dir.mkdir(parents=True, exist_ok=True)
            for task in tasks:
                module_path = gen_dir / task.module
                if resume and module_path.exists():
                    continue
                try:
                    result = run_bare_task(
                        client, model["id"], task, temperature=temperature
                    )
                except BudgetExceededError:
                    print(f"BUDGET ABORT after ${tracker.spent:.4f}", file=sys.stderr)
                    raise
                tracker.add(result.cost)
                (gen_dir / f"{task.name}.reply.md").write_text(result.content)
                module_path.write_text(
                    result.code
                    if result.code is not None
                    else "# no code block in model reply\n"
                )
                # Hashed at run time so Phase 2's prompt_sha256 field can be
                # backfilled truthfully (a prompt edited between the one-off
                # and the expansion is unrecoverable otherwise).
                from geocase.benchmark.runner.bare import bare_prompt

                prompt_sha = hashlib.sha256(bare_prompt(task).encode()).hexdigest()
                meta = {
                    "task": task.name,
                    "model": model["id"],
                    "trial": trial,
                    "track": "bare",
                    "protocol": "openrouter-chat",
                    "prompt_sha256": prompt_sha,
                    "cost_usd": result.cost,
                    "usage": result.usage,
                    "extracted": result.code is not None,
                }
                (gen_dir / f"{task.name}.meta.json").write_text(
                    json.dumps(meta, indent=2)
                )
                # This reports extraction only — whether a code block came back
                # and was written to disk. Correctness is not known until the
                # grading pass below.
                print(
                    f"{model['id']} trial {trial} {task.name}: "
                    f"{'code received' if result.code else 'NO CODE BLOCK'} "
                    f"(spent ${tracker.spent:.4f})"
                )
            print(f"grading {model['id']} trial {trial} ...")
            outcomes = grade_in_subprocess(gen_dir)
            graded = [o.model_dump(mode="json") for o in outcomes]
            (gen_dir / "graded.json").write_text(json.dumps(graded, indent=2))
            _print_verdicts(model["id"], trial, outcomes)
    print(f"done; total spend ${tracker.spent:.4f}")


def _print_verdicts(model_id: str, trial: int, outcomes: list[TrialOutcome]) -> None:
    for o in sorted(outcomes, key=lambda o: o.task):
        edge_detail = next(
            (
                c.detail
                for c in o.checks
                if c.status.value in ("SILENT", "LOUD") and c.kind is not None
            ),
            "",
        )
        print(f"  {o.task:<22} {o.outcome:<8} {edge_detail[:90]}")
    counts = Counter(o.outcome for o in outcomes)
    n = len(outcomes)
    silent = counts.get("SILENT", 0)
    print(
        f"{model_id} trial {trial}: "
        f"{counts.get('CORRECT', 0)} CORRECT, {silent} SILENT, "
        f"{counts.get('LOUD', 0)} LOUD, {counts.get('MISSING', 0)} MISSING "
        f"of {n} — silent-failure rate {silent / n:.0%}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="geocase.benchmark run")
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument(
        "--track",
        choices=["bare"],
        default="bare",
        help="agentic is manual-protocol-only in the one-off cut",
    )
    ap.add_argument(
        "--trials",
        type=int,
        default=None,
        help="override defaults.trials from the config",
    )
    ap.add_argument("--out", type=Path, default=Path("results/runs"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args(argv)

    config = yaml.safe_load(args.config.read_text())
    if args.trials is not None:
        config.setdefault("defaults", {})["trials"] = args.trials

    plan = plan_run(config, track=args.track)
    ceiling = (
        f"${plan.budget_ceiling_usd:.2f}"
        if plan.budget_ceiling_usd is not None
        else "UNLIMITED (set budget.max_usd_total!)"
    )
    print(
        f"track={args.track}: {len(plan.models)} models x {plan.trials} trials x "
        f"{plan.calls // max(len(plan.models) * plan.trials, 1)} tasks "
        f"= {plan.calls} API calls; budget ceiling {ceiling}"
    )
    if args.dry_run:
        return 0

    run_bare_track(config, out_root=args.out, resume=not args.no_resume)
    return 0


if __name__ == "__main__":
    sys.exit(main())
