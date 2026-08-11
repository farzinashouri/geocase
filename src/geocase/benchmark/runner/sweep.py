"""``python -m geocase.benchmark sweep`` — one entry point (Plan 17 §2.1).

Replaces "six scripts held together by the operator's memory" with a single
staged command::

    python -m geocase.benchmark sweep --config configs/models.yaml --domain geo \\
      --stages probe,run,grade,report --trials 3 [--dry-run] [--yes]

Stages are **separately resumable and idempotent, driven by what is on disk** —
there is deliberately no state file, because a state file is one more thing that
can disagree with reality. ``probe`` skips tasks already recorded, ``run`` skips
modules that exist and are not ``api_failure``, ``grade`` regrades any trial
whose ``graded.json`` is missing or older than its newest module.

The ``report`` stage **refuses to run while any ``named_trap`` is null**. That
keeps the U7/U8 review manual while making the blocker impossible to miss.
``scripts/judge_probes.py`` is deliberately *not* wired in: making LLM-as-judge
the path of least resistance would corrode a benchmark whose entire premise is
deterministic assertion.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from geocase.benchmark.registry import TaskMeta
from geocase.benchmark.runner import status as status_mod
from geocase.benchmark.runner.orchestrator import (
    confirm_estimate,
    plan_run,
    print_plan,
    run_bare_track,
)
from geocase.benchmark.runner.policy import add_pacing_args, policy_from_args

STAGES = ("probe", "run", "grade", "report")
REPO_ROOT = Path(__file__).resolve().parents[4]


def _parse_stages(raw: str) -> list[str]:
    stages = [s.strip() for s in raw.split(",") if s.strip()]
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        raise ValueError(f"unknown stage(s) {unknown}; known: {list(STAGES)}")
    # Canonical order regardless of how they were typed: grading before the
    # run it grades would silently report the previous run's numbers.
    return [s for s in STAGES if s in stages]


def stage_probe(args: argparse.Namespace, *, extra: list[str]) -> int:
    """Delegate to the probe script, which already resumes off disk."""
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "contamination_probe.py"),
        "--config",
        str(args.config),
        "--out",
        str(args.probes),
        *extra,
    ]
    if args.domain:
        cmd += ["--domain", args.domain]
    if args.dry_run:
        cmd.append("--dry-run")
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def stage_run(args: argparse.Namespace, config: dict, tasks: list[TaskMeta]) -> int:
    plan = plan_run(config, track="bare", tasks=tasks)
    print_plan(plan)
    pacing = policy_from_args(args, config)
    print(pacing.describe())
    if args.dry_run:
        return 0
    if not confirm_estimate(plan, yes=args.yes):
        return 3
    run_bare_track(config, out_root=args.runs, tasks=tasks, resume=True, pacing=pacing)
    return 0


def _needs_regrade(trial_dir: Path) -> bool:
    graded = trial_dir / "graded.json"
    if not graded.is_file():
        return True
    newest = max((p.stat().st_mtime for p in trial_dir.glob("*.py")), default=0.0)
    return newest > graded.stat().st_mtime


def stage_grade(args: argparse.Namespace, config: dict, tasks: list[TaskMeta]) -> int:
    from geocase.benchmark.grading import grade_in_subprocess
    from geocase.benchmark.runner.record import backfill_bare_record

    model_ids = [m["id"] for m in config.get("models", [])]
    runs = status_mod.scan_runs(args.runs, model_ids=model_ids)
    regraded = 0
    for run in runs:
        touched = False
        for trial in run.trials:
            trial_dir = run.run_dir / "generated" / trial.name
            if not _needs_regrade(trial_dir):
                continue
            print(f"grading {trial_dir} ...")
            if args.dry_run:
                regraded += 1
                continue
            outcomes = grade_in_subprocess(trial_dir, tasks=tasks)
            (trial_dir / "graded.json").write_text(
                json.dumps([o.model_dump(mode="json") for o in outcomes], indent=2)
            )
            regraded += 1
            touched = True
        # Keep run.json in step with the gradings it summarises, and give the
        # pre-Plan-17 runs the record they never had.
        if touched or not run.has_record:
            if not args.dry_run:
                backfill_bare_record(run.run_dir)
    print(f"{regraded} trial(s) {'would be ' if args.dry_run else ''}regraded")
    return 0


def stage_report(args: argparse.Namespace, config: dict) -> int:
    """Blocked while any probe reply is unreviewed (U7/U8 stay manual)."""
    model_ids = [m["id"] for m in config.get("models", [])]
    probes = status_mod.scan_probes(args.probes, model_ids=model_ids)
    unreviewed = [p for p in probes if p.unreviewed]
    if unreviewed:
        total = sum(p.unreviewed for p in unreviewed)
        print(
            f"report BLOCKED: {total} probe reply(ies) still have "
            f"named_trap=null across {len(unreviewed)} model(s). A null is not "
            f"a false — it means the probe is not yet usable as evidence. "
            f"Review them by hand (U7):",
            file=sys.stderr,
        )
        for p in unreviewed:
            print(
                f"  python scripts/review_probes.py {p.path}  "
                f"({p.unreviewed} of {p.landed} unreviewed)",
                file=sys.stderr,
            )
        return 1
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "probe_report.py")]
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="geocase.benchmark sweep")
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--domain", default=None)
    ap.add_argument("--tasks", nargs="*", default=None)
    ap.add_argument(
        "--stages",
        default="probe,run,grade,report",
        help=f"comma-separated subset of {','.join(STAGES)}",
    )
    ap.add_argument("--trials", type=int, default=None)
    ap.add_argument("--runs", type=Path, default=Path("results/runs"))
    ap.add_argument("--probes", type=Path, default=Path("results/probes"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    add_pacing_args(ap)
    args = ap.parse_args(argv)

    try:
        stages = _parse_stages(args.stages)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not stages:
        print("error: --stages selected nothing", file=sys.stderr)
        return 2

    config = yaml.safe_load(args.config.read_text())
    if args.trials is not None:
        config.setdefault("defaults", {})["trials"] = args.trials
    if args.max_usd is not None:
        config.setdefault("budget", {})["max_usd_total"] = args.max_usd

    from geocase.benchmark.cli import EmptySelectionError, select_tasks

    try:
        tasks = select_tasks(args.tasks, args.domain)
    except EmptySelectionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Pacing flags are forwarded to the probe script rather than re-derived, so
    # the two entry points cannot pace differently within one sweep.
    probe_extra: list[str] = []
    for flag, value in (
        ("--rpm", args.rpm),
        ("--requests-per-day", args.requests_per_day),
        ("--max-retry-after", args.max_retry_after),
        ("--task-budget", args.task_budget),
    ):
        if value is not None:
            probe_extra += [flag, str(value)]
    if args.honor_retry_after:
        probe_extra.append("--honor-retry-after")

    for stage in stages:
        print(f"\n=== {stage} ===")
        if stage == "probe":
            rc = stage_probe(args, extra=probe_extra)
        elif stage == "run":
            rc = stage_run(args, config, tasks)
        elif stage == "grade":
            rc = stage_grade(args, config, tasks)
        else:
            rc = stage_report(args, config)
        if rc:
            print(f"stage {stage} exited {rc}; stopping", file=sys.stderr)
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
