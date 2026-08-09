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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "run":
        # Lazy import: the runner needs httpx (the `bench` extra); grading not.
        from geocase.benchmark.runner.orchestrator import main as run_main

        return run_main(argv[1:])

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
