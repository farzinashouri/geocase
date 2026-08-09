"""Module loading and grading.

Ported from the Step 0 grader's ``load()``/``run_check()``. ``grade_module``
imports the generated module into the current process and is therefore only
for code that is already trusted (committed, human-reviewed modules — the pin
tests). Fresh model output goes through ``grade_in_subprocess``, which runs
the CLI in a child interpreter so untrusted code is never imported here.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from geocase.benchmark.registry import TaskMeta, all_tasks
from geocase.benchmark.taxonomy import (
    CheckKind,
    CheckResult,
    Status,
    TrialOutcome,
    aggregate_outcome,
)


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_grader(task: TaskMeta):
    return load_module(task.grader_path)


def grade_module(task: TaskMeta, gen_dir: Path) -> TrialOutcome:
    """Grade ``gen_dir/<task.module>`` against the task's oracle checks."""
    module_path = gen_dir / task.module
    if not module_path.exists():
        checks = [
            CheckResult(
                check="import",
                kind=None,
                status=Status.MISSING,
                detail=f"{task.module} or function absent",
            )
        ]
        return TrialOutcome(task=task.name, outcome="MISSING", checks=checks)

    try:
        mod = load_module(module_path)
    except Exception as exc:  # noqa: BLE001 — import-time crash is LOUD
        checks = [
            CheckResult(
                check="import",
                kind=None,
                status=Status.LOUD,
                detail=f"{type(exc).__name__}: {exc}",
            )
        ]
        return TrialOutcome(task=task.name, outcome="LOUD", checks=checks)

    fn = getattr(mod, task.function, None)
    if fn is None:
        checks = [
            CheckResult(
                check="import",
                kind=None,
                status=Status.MISSING,
                detail=f"{task.module} or function absent",
            )
        ]
        return TrialOutcome(task=task.name, outcome="MISSING", checks=checks)

    grader = _load_grader(task)
    results = []
    for name, kind, check_fn in grader.build_checks(fn):
        try:
            ok, detail = check_fn()
        except Exception as exc:  # noqa: BLE001 — loud failure is a grading outcome
            results.append(
                CheckResult(
                    check=name,
                    kind=CheckKind(kind),
                    status=Status.LOUD,
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        results.append(
            CheckResult(
                check=name,
                kind=CheckKind(kind),
                status=Status.PASS if ok else Status.SILENT,
                detail=str(detail),
            )
        )
    return TrialOutcome(
        task=task.name, outcome=aggregate_outcome(results), checks=results
    )


def grade_directory(
    gen_dir: Path, tasks: list[TaskMeta] | None = None
) -> list[TrialOutcome]:
    return [grade_module(task, gen_dir) for task in (tasks or all_tasks())]


def grade_in_subprocess(
    gen_dir: Path, *, python: str | Path = sys.executable, timeout: float = 600
) -> list[TrialOutcome]:
    """Grade untrusted generated modules in a child interpreter via the CLI."""
    proc = subprocess.run(
        [
            str(python),
            "-m",
            "geocase.benchmark",
            "grade",
            "--generated",
            str(gen_dir),
            "--json",
            "/dev/stdout",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    records = json.loads(proc.stdout)
    by_task: dict[str, list[CheckResult]] = {}
    for r in records:
        by_task.setdefault(r["op"], []).append(
            CheckResult(
                check=r["check"],
                kind=None if r["kind"] == "-" else CheckKind(r["kind"]),
                status=Status(r["status"]),
                detail=r["detail"],
            )
        )
    return [
        TrialOutcome(task=name, outcome=aggregate_outcome(checks), checks=checks)
        for name, checks in by_task.items()
    ]
