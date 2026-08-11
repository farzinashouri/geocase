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
from geocase.benchmark.runner.policy import Pacing, add_pacing_args, policy_from_args
from geocase.benchmark.runner.record import write_bare_record
from geocase.benchmark.taxonomy import TrialOutcome

# Measured over the committed bare runs (n=65): 221 prompt / 3164 completion
# tokens per task. Used only to estimate spend before a run; the hard budget
# abort is always enforced against OpenRouter's own returned usage.cost.
EST_PROMPT_TOKENS = 221
EST_COMPLETION_TOKENS = 3164


@dataclass
class RunPlan:
    calls: int
    models: list[str]
    trials: int
    budget_ceiling_usd: float | None
    est_usd: float | None = None
    est_by_model: dict[str, float] | None = None
    # Models whose config carries no `pricing:` block. Their spend is not in
    # est_usd, so an estimate that ignored them would read as cheaper than the
    # run can be — they are named instead of silently dropped.
    unpriced: list[str] | None = None


def _models_for_track(config: dict, track: str) -> list[dict]:
    return [m for m in config.get("models", []) if track in m.get("tracks", [])]


def _est_model_usd(model: dict, calls: int) -> float | None:
    """Estimated spend for one model, or None when it carries no prices."""
    pricing = model.get("pricing") or {}
    try:
        prompt_usd = float(pricing["prompt_usd_per_1m"])
        completion_usd = float(pricing["completion_usd_per_1m"])
    except (KeyError, TypeError, ValueError):
        return None
    per_call = (
        EST_PROMPT_TOKENS * prompt_usd + EST_COMPLETION_TOKENS * completion_usd
    ) / 1_000_000
    return per_call * calls


def plan_run(
    config: dict, *, track: str, tasks: list[TaskMeta] | None = None
) -> RunPlan:
    models = _models_for_track(config, track)
    trials = int(config.get("defaults", {}).get("trials", 1))
    # Same task list the run will use, so --dry-run's call count and cost
    # ceiling stay truthful under a --domain filter.
    n_tasks = len(all_tasks() if tasks is None else tasks)
    calls_per_model = trials * n_tasks

    est_by_model: dict[str, float] = {}
    unpriced: list[str] = []
    for m in models:
        est = _est_model_usd(m, calls_per_model)
        if est is None:
            unpriced.append(m["id"])
        else:
            est_by_model[m["id"]] = est
    return RunPlan(
        calls=len(models) * calls_per_model,
        models=[m["id"] for m in models],
        trials=trials,
        budget_ceiling_usd=config.get("budget", {}).get("max_usd_total"),
        est_usd=sum(est_by_model.values()) if est_by_model else None,
        est_by_model=est_by_model,
        unpriced=unpriced,
    )


def print_plan(plan: RunPlan, *, track: str = "bare") -> None:
    """The dry-run summary: call count *and* estimated spend, per model."""
    ceiling = (
        f"${plan.budget_ceiling_usd:.2f}"
        if plan.budget_ceiling_usd is not None
        else "UNLIMITED (set budget.max_usd_total!)"
    )
    print(
        f"track={track}: {len(plan.models)} models x {plan.trials} trials x "
        f"{plan.calls // max(len(plan.models) * plan.trials, 1)} tasks "
        f"= {plan.calls} API calls; budget ceiling {ceiling}"
    )
    for model_id, est in sorted(
        (plan.est_by_model or {}).items(), key=lambda kv: -kv[1]
    ):
        print(f"  {model_id:<40} est ${est:.2f}")
    for model_id in plan.unpriced or []:
        # Named rather than counted as $0: an estimate that silently omits a
        # model reads as cheaper than the run can actually be.
        print(f"  {model_id:<40} est UNKNOWN (no pricing: in config)")
    if plan.est_usd is not None:
        print(f"  estimated total ${plan.est_usd:.2f} (excludes OpenRouter's fee)")


def confirm_estimate(plan: RunPlan, *, yes: bool = False) -> bool:
    """Refuse to start a run whose estimate is over half the budget ceiling."""
    if yes or plan.est_usd is None or plan.budget_ceiling_usd is None:
        return True
    if plan.est_usd <= 0.5 * plan.budget_ceiling_usd:
        return True
    print(
        f"refusing to start: estimated ${plan.est_usd:.2f} is over half the "
        f"${plan.budget_ceiling_usd:.2f} ceiling. Re-run with --yes if that is "
        f"intended, or lower --trials / narrow the roster.",
        file=sys.stderr,
    )
    return False


def _slug(model_id: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", model_id.lower())


def _run_dir_suffix(tasks: list[TaskMeta]) -> str:
    """Partition run directories by domain.

    Geo keeps the bare ``{date}_{slug}_bare`` name, preserving the committed
    run paths and their resume behaviour; every other domain is suffixed. A
    mixed-domain run is refused outright: its outcomes could only be reported
    as a cross-domain aggregate, which is noise dressed as a finding (trap 12).
    """
    domains = sorted({t.domain for t in tasks})
    if len(domains) > 1:
        raise ValueError(
            f"refusing a mixed-domain run over {domains}: rates are not "
            f"comparable across domains (Plan 16, trap 12) — pass --domain"
        )
    return "" if domains == ["geo"] else f"_{domains[0]}"


def run_bare_track(
    config: dict,
    *,
    out_root: Path,
    tasks: list[TaskMeta] | None = None,
    resume: bool = True,
    pacing: Pacing | None = None,
) -> None:
    # Imported here so --dry-run and the unit tests never need credentials.
    from geocase.benchmark.runner.bare import run_bare_task

    tasks = tasks or all_tasks()
    suffix = _run_dir_suffix(tasks)
    defaults = config.get("defaults", {})
    trials = int(defaults.get("trials", 1))
    temperature = defaults.get("temperature")
    budget = config.get("budget", {})
    max_usd_total = (
        budget.get("max_usd_total") if pacing is None else pacing.max_usd_total
    )
    # A per-model ceiling so one long-running reasoning model cannot eat the
    # whole budget before the cheap models are ever reached.
    max_usd_per_model = budget.get("max_usd_per_model")
    tracker = CostTracker(max_usd_total)
    client = OpenRouterClient() if pacing is None else pacing.build_client()
    date = dt.date.today().isoformat()
    failures: Counter[str] = Counter()

    for model in _models_for_track(config, "bare"):
        run_dir = out_root / f"{date}_{_slug(model['id'])}_bare{suffix}"
        model_tracker = CostTracker(max_usd_per_model)
        model_cost = 0.0
        outcomes_by_trial: dict[int, list[TrialOutcome]] = {}
        over_model_budget = False
        for trial in range(1, trials + 1):
            gen_dir = run_dir / "generated" / f"trial{trial}"
            gen_dir.mkdir(parents=True, exist_ok=True)
            for task in tasks:
                if over_model_budget:
                    break
                module_path = gen_dir / task.module
                if (
                    resume
                    and module_path.exists()
                    and not _is_api_failure(gen_dir / f"{task.name}.meta.json")
                ):
                    continue
                try:
                    result = run_bare_task(
                        client, model["id"], task, temperature=temperature
                    )
                except BudgetExceededError:
                    print(f"BUDGET ABORT after ${tracker.spent:.4f}", file=sys.stderr)
                    raise
                except Exception as exc:  # noqa: BLE001 - see comment
                    # Not fatal: any API-side failure (timeout, exhausted 429
                    # retries, provider 5xx, malformed reply) is recorded as a
                    # failed task — it grades as MISSING, since no module came
                    # back — and the run goes on to the next task. Only the
                    # budget abort above is allowed to stop the run.
                    _write_failure(gen_dir, task, model["id"], trial, exc)
                    failures[model["id"]] += 1
                    print(
                        f"{model['id']} trial {trial} {task.name}: "
                        f"FAILED ({type(exc).__name__}: {exc}) "
                        f"(spent ${tracker.spent:.4f})",
                        file=sys.stderr,
                    )
                    continue
                tracker.add(result.cost)
                # Per-model ceiling checked after the global one, so a run
                # that trips it skips to the next model instead of aborting.
                try:
                    model_tracker.add(result.cost)
                except BudgetExceededError as exc:
                    print(
                        f"{model['id']}: per-model budget reached ({exc}) — "
                        f"moving to the next model",
                        file=sys.stderr,
                    )
                    over_model_budget = True
                model_cost += result.cost or 0.0
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
            try:
                outcomes = grade_in_subprocess(gen_dir, tasks=tasks)
            except Exception as exc:  # noqa: BLE001
                # The generated code is already on disk and can be re-graded
                # offline, so a grading crash must not cost the remaining models.
                print(
                    f"{model['id']} trial {trial}: GRADING FAILED "
                    f"({type(exc).__name__}: {exc}) — generations kept at "
                    f"{gen_dir}, re-grade offline",
                    file=sys.stderr,
                )
                continue
            graded = [o.model_dump(mode="json") for o in outcomes]
            (gen_dir / "graded.json").write_text(json.dumps(graded, indent=2))
            outcomes_by_trial[trial] = outcomes
            _print_verdicts(model["id"], trial, outcomes)
        # One run.json per model, written even when trials failed to grade —
        # its whole purpose is to record that a run is incomplete.
        record = write_bare_record(
            run_dir,
            model=model,
            trials=trials,
            date=date,
            config=config,
            outcomes_by_trial=outcomes_by_trial,
            cost_usd=model_cost,
            domain=tasks[0].domain,
        )
        integrity = record["integrity"]
        if not integrity["publishable"]:
            print(
                f"{model['id']}: NOT PUBLISHABLE — {integrity['api_failures']} of "
                f"{integrity['tasks_attempted']} task(s) failed at the API. "
                f"Any rate over this run has those in its denominator; re-run "
                f"before quoting it.",
                file=sys.stderr,
            )
    print(f"done; total spend ${tracker.spent:.4f}")
    if failures:
        # Loud on purpose: these tasks have no model answer behind them, so any
        # score computed over this run is incomplete until they are re-run.
        total = sum(failures.values())
        print(f"{total} task(s) failed at the API and were NOT scored:")
        for model_id, n in failures.most_common():
            print(f"  {model_id}: {n}")
        print("re-run the same command to retry only the failed tasks")


def _is_api_failure(meta_path: Path) -> bool:
    """True for tasks a previous run recorded as an API failure.

    Resume re-attempts these: a rate-limited task has no result yet, and
    skipping it would silently bake a transient 429 into the scores."""
    try:
        return json.loads(meta_path.read_text()).get("status") in (
            "api_failure",
            "timeout",  # written by earlier runs, before the rename
        )
    except (OSError, ValueError):
        return False


def _write_failure(
    gen_dir: Path, task: TaskMeta, model_id: str, trial: int, exc: BaseException
) -> None:
    """Record a failed task on disk so grading sees it as MISSING.

    ``status: api_failure`` in the meta marks it as a runner/API failure rather
    than a model that answered badly — the two must not be confused when the
    silent-failure rate is read off these files."""
    detail = f"{type(exc).__name__}: {exc}"
    (gen_dir / f"{task.name}.reply.md").write_text(f"<!-- api failure: {detail} -->\n")
    (gen_dir / task.module).write_text(f"# api failure: {detail}\n")
    meta = {
        "task": task.name,
        "model": model_id,
        "trial": trial,
        "track": "bare",
        "protocol": "openrouter-chat",
        "status": "api_failure",
        "error_type": type(exc).__name__,
        "detail": detail,
        "cost_usd": None,
        "usage": {},
        "extracted": False,
    }
    (gen_dir / f"{task.name}.meta.json").write_text(json.dumps(meta, indent=2))


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
    if not n:
        print(f"{model_id} trial {trial}: no graded outcomes")
        return
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
    ap.add_argument(
        "--domain",
        default=None,
        help="which domain's tasks to run; required once more than one exists",
    )
    ap.add_argument(
        "--tasks", nargs="*", default=None, help="task names to run (default: all)"
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument(
        "--yes",
        action="store_true",
        help="confirm a run whose estimate is over half the budget ceiling",
    )
    add_pacing_args(ap)
    args = ap.parse_args(argv)

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

    try:
        # Fails the same way under --dry-run as under a real run: an operator
        # must never learn a run was refused only after it was launched.
        _run_dir_suffix(tasks)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    plan = plan_run(config, track=args.track, tasks=tasks)
    pacing = policy_from_args(args, config)
    print_plan(plan, track=args.track)
    print(pacing.describe())
    if args.dry_run:
        return 0
    if not confirm_estimate(plan, yes=args.yes):
        return 3

    try:
        run_bare_track(
            config,
            out_root=args.out,
            tasks=tasks,
            resume=not args.no_resume,
            pacing=pacing,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
