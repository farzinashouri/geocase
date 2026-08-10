"""``python -m geocase.benchmark grade`` — reproduces the Step 0 grader CLI.

The command is agnostic to who wrote the modules: any directory whose files
match the task contracts grades identically, model-written or hand-written.
JSON output keeps the Step 0 record shape: ``{op, check, kind, status,
detail}`` with ``kind: "-"`` for module-level records.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from geocase.benchmark.grading import grade_directory
from geocase.benchmark.registry import all_tasks
from geocase.benchmark.taxonomy import TrialOutcome


def _records(outcomes: list[TrialOutcome]) -> list[dict]:
    return [
        {
            "op": o.task,
            "check": c.check,
            "kind": c.kind.value if c.kind else "-",
            "status": c.status.value,
            "detail": c.detail,
        }
        for o in outcomes
        for c in o.checks
    ]


def _print_table(outcomes: list[TrialOutcome]) -> None:
    rows = _records(outcomes)
    wid = max(len(r["op"]) for r in rows) if rows else 10
    print(f"{'operation':<{wid}}  {'check':<28} {'kind':<8} {'status':<8} detail")
    for r in rows:
        print(
            f"{r['op']:<{wid}}  {r['check']:<28} {r['kind']:<8} "
            f"{r['status']:<8} {r['detail']}"
        )

    silent = sum(1 for o in outcomes if o.outcome == "SILENT")
    loud = sum(1 for o in outcomes if o.outcome == "LOUD")
    clean = sum(1 for o in outcomes if o.outcome == "CORRECT")
    print(
        f"\nper-operation: {clean} fully correct, {silent} with SILENT failures, "
        f"{loud} with only LOUD failures, of {len(outcomes)} graded"
    )


def _manual_main(argv: list[str]) -> int:
    """`manual prepare` / `manual ingest` — the coding-agent-CLI protocol."""
    import datetime as dt

    from geocase.benchmark.runner.manual import PROTOCOLS, ingest, prepare

    ap = argparse.ArgumentParser(prog="geocase.benchmark manual")
    sub = ap.add_subparsers(dest="action", required=True)

    prep = sub.add_parser(
        "prepare", help="build an agent workdir with rendered prompts"
    )
    prep.add_argument("--out", type=Path, required=True)
    prep.add_argument(
        "--no-venv",
        action="store_true",
        help="skip building the sandbox venv (it takes minutes)",
    )
    prep.add_argument("--seed", type=int, default=None, help="seed the session order")

    ing = sub.add_parser(
        "ingest", help="grade a completed session set into a run record"
    )
    ing.add_argument("--dir", type=Path, required=True)
    ing.add_argument("--model-id", required=True, help="e.g. anthropic/claude-fable-5")
    ing.add_argument("--label", default=None, help="display name (default: --model-id)")
    ing.add_argument("--protocol", required=True, choices=sorted(PROTOCOLS))
    ing.add_argument("--trial", type=int, required=True)
    ing.add_argument("--out", type=Path, default=Path("results/runs"))
    ing.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    args = ap.parse_args(argv)

    if args.action == "prepare":
        p = prepare(args.out, create_venv=not args.no_venv, seed=args.seed)
        print(f"workdir ready: {p.workdir}")
        if p.python:
            print(f"interpreter:   {p.python}")
        else:
            print("interpreter:   NOT BUILT (--no-venv); agents cannot run code")
        print(f"prompts:       {p.workdir / 'prompts'} ({len(p.prompts)} tasks)")
        print("\nRun one FRESH agent session per task, in this order:")
        print(
            "  cwd = the workdir, no repo access, prompt pasted verbatim, run to DONE."
        )
        for i, name in enumerate(p.order, 1):
            print(f"  {i:>2}. {name}")
        return 0

    record = ingest(
        args.dir,
        out_root=args.out,
        model_id=args.model_id,
        label=args.label or args.model_id,
        protocol=args.protocol,
        trial=args.trial,
        date=args.date or dt.date.today().isoformat(),
    )
    counts: dict[str, int] = {}
    for task in record["tasks"].values():
        for t in task["trials"]:
            if t["trial"] == args.trial:
                counts[t["outcome"]] = counts.get(t["outcome"], 0) + 1
    total = sum(counts.values()) or 1
    print(f"ingested trial {args.trial} into {args.out / record['run_id']}")
    print(
        f"  {counts.get('CORRECT', 0)} CORRECT, {counts.get('SILENT', 0)} SILENT, "
        f"{counts.get('LOUD', 0)} LOUD, {counts.get('MISSING', 0)} MISSING "
        f"of {total} — silent-failure rate {counts.get('SILENT', 0) / total:.0%}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "run":
        # Lazy import: the runner needs httpx (the `bench` extra); grading not.
        from geocase.benchmark.runner.orchestrator import main as run_main

        return run_main(argv[1:])
    if argv and argv[0] == "manual":
        return _manual_main(argv[1:])

    ap = argparse.ArgumentParser(prog="geocase.benchmark")
    sub = ap.add_subparsers(dest="command", required=True)
    grade = sub.add_parser("grade", help="grade a directory of generated modules")
    grade.add_argument("--generated", type=Path, required=True)
    grade.add_argument("--json", type=Path, default=None)
    grade.add_argument(
        "--tasks", nargs="*", default=None, help="task names to grade (default: all)"
    )
    grade.add_argument(
        "--quiet", action="store_true", help="suppress the table (JSON output only)"
    )
    args = ap.parse_args(argv)

    tasks = all_tasks()
    if args.tasks:
        tasks = [t for t in tasks if t.name in set(args.tasks)]
    outcomes = grade_directory(args.generated, tasks)

    if not args.quiet:
        _print_table(outcomes)
    if args.json:
        payload = json.dumps(_records(outcomes), indent=2)
        if str(args.json) == "/dev/stdout":
            print(payload)
        else:
            args.json.write_text(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
