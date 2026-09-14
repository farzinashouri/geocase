"""``python -m geocase.benchmark report`` (Plan 46 §2.2).

The command whose absence meant two runs could not be compared: a task x
model matrix, a per-``trap_category`` rate, and any notion of reproducibility
across trials all had to be assembled by hand from ``run.json`` files.

Everything is read off the schema v2 ``run.json`` records and computed at
report time — ``trapped`` vs ``broken`` in particular is derived from the
stored ``checks`` and never written back, so no committed record moves.

Five tables and **no blended headline number**:

1. task x model matrix — one cell per task, the k-trial classifications side
   by side (``C T T`` reads as one flaky task; ``T T T`` reads as a defect);
2. per-``trap_category`` rollup — trapped rate per category per column, with
   a Wilson interval, since 5 of 20 is not a percentage worth quoting bare;
3. reproducible-silent — tasks trapped in **every** trial at k>=3, the
   strongest single output the benchmark can produce;
4. duration — seconds inside the model calls, summed per trial and a median
   per call, read off each call's meta (``usage.duration_s``). On the effort
   track no dollars are billed, so this is the price of an effort level;
5. (``--coverage``) which catalog risk families no task in the domain
   exercises, read off :data:`~geocase.benchmark.taxonomy.TRAP_TO_RISK`.

A run whose ``integrity.publishable`` is false is excluded from every rate
and **named** as excluded: a rate computed over rate-limit damage is the
benchmark's own silent failure. Cross-domain aggregation stays refused.
Effort columns carry their ``preamble`` marker in the header, so an effort
column can never be read beside a bare column without the reader seeing why
not.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from geocase.benchmark.registry import TaskMeta
from geocase.benchmark.runner.status import scan_runs
from geocase.benchmark.taxonomy import (
    TRAP_TO_RISK,
    CheckResult,
    TrialClass,
    classify_trial,
)

#: One letter per classification, for the matrix cells.
LETTER: dict[str, str] = {
    "correct": "C",
    "trapped": "T",
    "broken": "B",
    "loud": "L",
    "missing": "M",
}

# The five effort levels in axis order, so effort columns sort low -> max
# rather than alphabetically (which would put max before medium).
_EFFORT_ORDER = {"low": 0, "medium": 1, "high": 2, "xhigh": 3, "max": 4}


@dataclass
class RunView:
    run_id: str
    model_id: str
    label: str
    domain: str
    track: str
    trials: int
    effort: str | None
    preamble: str | None
    #: task -> [(trial, classification)], trial-ordered.
    classes: dict[str, list[tuple[int, TrialClass]]] = field(default_factory=dict)
    #: [(trial, seconds or None)] per timed call, read off the metas — never
    #: off ``run.json``, so committed records need not move to gain a clock.
    call_seconds: list[tuple[int, float | None]] = field(default_factory=list)

    @property
    def column(self) -> str:
        """The column header: label, effort level, and the preamble marker.

        The marker is not decoration. Without it an effort column eventually
        gets read beside a bare column and something false is concluded
        about a model (Plan 45 §4)."""
        name = self.label
        if self.effort:
            name += f" @{self.effort}"
        if self.preamble:
            name += f" [{self.preamble}]"
        return name

    @property
    def sort_key(self) -> tuple:
        return (self.track, self.label, _EFFORT_ORDER.get(self.effort or "", -1))


@dataclass
class ExcludedRun:
    run_id: str
    reason: str


@dataclass
class Rate:
    trapped: int
    broken: int
    n: int
    low: float
    high: float

    @property
    def rate(self) -> float:
        return self.trapped / self.n if self.n else 0.0


@dataclass
class Duration:
    """Seconds spent inside the model calls of one column.

    Summed per trial (the operator's "how long did one pass over the tasks
    take") and a median per call (robust to one stalled task). ``untimed``
    counts calls with no clock, so a run from before timing existed reads as
    "not recorded" rather than as fast."""

    per_trial: dict[int, float]
    median_s: float | None
    n: int
    untimed: int


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for ``k`` successes in ``n`` trials.

    Hand-rolled rather than imported: ten lines is cheaper than a scipy
    dependency, and the interval is the point — at n=20 it is wide enough to
    change what the number licenses you to say."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _view(run_dir: Path, record: dict) -> RunView:
    classes: dict[str, list[tuple[int, TrialClass]]] = {}
    for task, entry in (record.get("tasks") or {}).items():
        rows = []
        for trial in entry.get("trials") or []:
            checks = [CheckResult.model_validate(c) for c in trial.get("checks") or []]
            rows.append((int(trial.get("trial", 0)), classify_trial(checks)))
        rows.sort()
        classes[task] = rows
    model = record.get("model") or {}
    return RunView(
        run_id=record.get("run_id") or run_dir.name,
        model_id=model.get("id", run_dir.name),
        label=model.get("label") or model.get("id", run_dir.name),
        domain=record.get("domain", "geo"),
        track=record.get("track", "bare"),
        trials=int((record.get("config") or {}).get("trials") or 0),
        effort=record.get("effort"),
        preamble=record.get("preamble"),
        classes=classes,
        call_seconds=_call_seconds(run_dir),
    )


def _call_seconds(run_dir: Path) -> list[tuple[int, float | None]]:
    """``(trial, usage.duration_s)`` for every answered call under ``generated/``.

    Failure metas (``status: api_failure``) carry no answer and are skipped:
    a 429 that took 0.1 s to arrive is not a fast model."""
    out: list[tuple[int, float | None]] = []
    for meta_path in sorted((run_dir / "generated").glob("trial*/*.meta.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        if meta.get("status"):
            continue
        seconds = (meta.get("usage") or {}).get("duration_s")
        trial = int(meta.get("trial") or meta_path.parent.name.removeprefix("trial"))
        out.append(
            (trial, float(seconds) if isinstance(seconds, (int, float)) else None)
        )
    return out


def load_runs(
    runs_root: Path,
    *,
    domain: str | None = None,
    track: str | None = None,
    model_ids: list[str] | None = None,
) -> tuple[list[RunView], list[ExcludedRun]]:
    """Every publishable run under ``runs_root``, plus the excluded ones by name.

    Discovery goes through :func:`status.scan_runs` so the two commands can
    never disagree about what is a run."""
    views: list[RunView] = []
    excluded: list[ExcludedRun] = []
    for status in scan_runs(runs_root, model_ids=model_ids):
        record_path = status.run_dir / "run.json"
        if not status.has_record:
            excluded.append(ExcludedRun(status.run_dir.name, "no run.json"))
            continue
        try:
            record = json.loads(record_path.read_text())
        except (OSError, ValueError) as exc:
            excluded.append(
                ExcludedRun(status.run_dir.name, f"unreadable run.json: {exc}")
            )
            continue
        view = _view(status.run_dir, record)
        if domain is not None and view.domain != domain:
            continue
        if track is not None and view.track != track:
            continue
        integrity = record.get("integrity") or {}
        if integrity.get("publishable") is not True:
            failures = integrity.get("api_failures")
            excluded.append(
                ExcludedRun(
                    view.run_id,
                    "not publishable"
                    + (f" ({failures} api_failure(s))" if failures else "")
                    + " — rate-limit damage is not model behaviour",
                )
            )
            continue
        views.append(view)
    views.sort(key=lambda v: v.sort_key)
    return views, excluded


# ------------------------------------------------------------------ tables


def build_matrix(
    runs: list[RunView], tasks: list[TaskMeta]
) -> dict[str, dict[str, list[str]]]:
    """``{task: {column: [letter per trial]}}``; a task a run never attempted
    gets ``["-"]`` rather than being dropped."""
    matrix: dict[str, dict[str, list[str]]] = {}
    for task in tasks:
        row: dict[str, list[str]] = {}
        for run in runs:
            rows = run.classes.get(task.name)
            row[run.column] = [LETTER[c] for _, c in rows] if rows else ["-"]
        matrix[task.name] = row
    return matrix


def category_rates(
    runs: list[RunView], tasks: list[TaskMeta]
) -> dict[str, dict[str, Rate]]:
    """``{column: {trap_category: Rate}}`` over every trial of every task in
    the category. ``broken`` trials are counted separately: they are in the
    denominator (the model was asked) but are not the phenomenon."""
    by_category: dict[str, list[TaskMeta]] = {}
    for task in tasks:
        by_category.setdefault(task.trap_category, []).append(task)
    out: dict[str, dict[str, Rate]] = {}
    for run in runs:
        col: dict[str, Rate] = {}
        for category, members in sorted(by_category.items()):
            trapped = broken = n = 0
            for task in members:
                for _, cls in run.classes.get(task.name, []):
                    n += 1
                    trapped += cls == "trapped"
                    broken += cls == "broken"
            if n:
                low, high = wilson_interval(trapped, n)
                col[category] = Rate(trapped, broken, n, low, high)
        out[run.column] = col
    return out


def reproducible_silent(
    runs: list[RunView], tasks: list[TaskMeta], *, min_trials: int = 3
) -> dict[str, list[str]]:
    """Tasks trapped in **every** trial, for runs with at least ``min_trials``.

    Below k=3 nothing is claimed: two agreeing trials cannot separate a
    reproducible defect from an unlucky pair, which is what Step 0 needed a
    second blind trial to establish for ``buffer_m``."""
    out: dict[str, list[str]] = {}
    for run in runs:
        hits = []
        for task in tasks:
            rows = run.classes.get(task.name, [])
            if len(rows) >= min_trials and all(c == "trapped" for _, c in rows):
                hits.append(task.name)
        out[run.column] = hits
    return out


def call_durations(runs: list[RunView]) -> dict[str, Duration]:
    """``{column: Duration}`` from the timed calls of each run."""
    out: dict[str, Duration] = {}
    for run in runs:
        per_trial: dict[int, float] = {}
        timed: list[float] = []
        untimed = 0
        for trial, seconds in run.call_seconds:
            if seconds is None:
                untimed += 1
                continue
            per_trial[trial] = per_trial.get(trial, 0.0) + seconds
            timed.append(seconds)
        timed.sort()
        median = None
        if timed:
            mid = len(timed) // 2
            median = timed[mid] if len(timed) % 2 else (timed[mid - 1] + timed[mid]) / 2
        out[run.column] = Duration(per_trial, median, len(timed), untimed)
    return out


def covered_risk_terms(tasks: list[TaskMeta]) -> dict[str, list[str]]:
    """``{risk term: [task names exercising it]}`` via ``TRAP_TO_RISK``."""
    out: dict[str, list[str]] = {}
    for task in tasks:
        for term in TRAP_TO_RISK.get(task.trap_category, ()):
            out.setdefault(term, []).append(task.name)
    return out


def uncovered_risk_families(tasks: list[TaskMeta]) -> list[str]:
    """Catalog risk families no task in ``tasks`` exercises.

    The family list is read off ``TRAP_TO_RISK``'s own terms plus the
    families the plan names as gaps, so this module still imports nothing
    from ``geocase.catalog``; ``test_trap_coverage.py`` cross-checks the
    terms against the real vocabulary."""
    covered = {term.split("/")[0] for term in covered_risk_terms(tasks)}
    return sorted(RISK_FAMILIES - covered)


#: Every family the catalog vocabulary has (``geocase.catalog.risk_types``),
#: restated here as data so this module stays catalog-free. The coverage test
#: asserts this set matches ``families()`` exactly.
RISK_FAMILIES: frozenset[str] = frozenset(
    {
        "attribute",
        "band",
        "crs",
        "data",
        "dtype",
        "extent",
        "failure_mode",
        "footprint",
        "format",
        "geometry",
        "measurement",
        "nodata",
        "precision",
        "scaling",
        "transform",
    }
)


# ---------------------------------------------------------------- rendering


def _fmt_rate(rate: Rate) -> str:
    return (
        f"{rate.trapped}/{rate.n} trapped ({rate.rate:.0%}; "
        f"95% CI {rate.low:.0%}-{rate.high:.0%})"
        + (f", {rate.broken} broken" if rate.broken else "")
    )


def render(
    runs: list[RunView],
    excluded: list[ExcludedRun],
    tasks: list[TaskMeta],
    *,
    domain: str,
    coverage: bool = False,
    out: TextIO | None = None,
) -> None:
    # Resolved at call time, not bound at import: pytest's capture and any
    # redirect of sys.stdout must see the report.
    out = out or sys.stdout
    columns = [r.column for r in runs]
    print(
        f"domain: {domain}   "
        "letters: C correct, T trapped, B broken, L loud, M missing",
        file=out,
    )
    print(
        "(trapped = every control passed and an edge returned a wrong value silently; "
        "broken = a control did not pass)",
        file=out,
    )
    if any(r.preamble for r in runs):
        print(
            "columns marked [claude-code-harness] saw the Claude Code preamble and are "
            "comparable within the effort track only",
            file=out,
        )

    print("\nTASK x MODEL", file=out)
    if not runs:
        print("  (no publishable runs)", file=out)
    else:
        wid = max(len(t.name) for t in tasks)
        matrix = build_matrix(runs, tasks)
        for i, col in enumerate(columns, 1):
            print(f"  [{i}] {col}  (k={runs[i - 1].trials})", file=out)
        print(
            f"  {'task':<{wid}}  "
            + "  ".join(f"[{i}]" for i in range(1, len(columns) + 1)),
            file=out,
        )
        for task in tasks:
            cells = "  ".join(f"{' '.join(matrix[task.name][c]):<5}" for c in columns)
            print(f"  {task.name:<{wid}}  {cells}", file=out)

    print("\nPER TRAP CATEGORY (trapped rate per column)", file=out)
    rates = category_rates(runs, tasks)
    for col in columns:
        print(f"  {col}", file=out)
        for category, rate in rates[col].items():
            print(f"    {category:<20} {_fmt_rate(rate)}", file=out)

    print("\nREPRODUCIBLE SILENT (trapped in every trial, k>=3)", file=out)
    repro = reproducible_silent(runs, tasks)
    for col in columns:
        run = next(r for r in runs if r.column == col)
        if run.trials < 3:
            print(f"  {col}: not claimed at k={run.trials}", file=out)
        else:
            print(f"  {col}: {', '.join(repro[col]) or 'none'}", file=out)

    print(
        "\nDURATION (seconds inside the model calls; pacing waits and grading "
        "excluded)",
        file=out,
    )
    for col, dur in call_durations(runs).items():
        if not dur.n:
            print(f"  {col}: not recorded", file=out)
            continue
        trials_txt = ", ".join(
            f"trial {t} {s:.0f}s" for t, s in sorted(dur.per_trial.items())
        )
        print(
            f"  {col}: {trials_txt}; median {dur.median_s:.1f}s per call "
            f"({dur.n} calls"
            + (f", {dur.untimed} untimed" if dur.untimed else "")
            + ")",
            file=out,
        )

    if coverage:
        print("\nCOVERAGE (catalog risk families, via TRAP_TO_RISK)", file=out)
        covered = covered_risk_terms(tasks)
        for term in sorted(covered):
            print(f"  {term:<40} {', '.join(sorted(set(covered[term])))}", file=out)
        gaps = uncovered_risk_families(tasks)
        print(f"  families no task exercises: {', '.join(gaps) or 'none'}", file=out)

    print("\nEXCLUDED", file=out)
    if not excluded:
        print("  none", file=out)
    for ex in excluded:
        print(f"  {ex.run_id}: {ex.reason}", file=out)


def main(argv: list[str] | None = None, *, out: TextIO | None = None) -> int:
    ap = argparse.ArgumentParser(prog="geocase.benchmark report")
    ap.add_argument("--runs", type=Path, default=Path("results/runs"))
    ap.add_argument("--domain", default=None)
    ap.add_argument("--track", default=None, help="restrict to one track")
    ap.add_argument(
        "--by-effort",
        action="store_true",
        help="restrict to the effort track (columns sort low -> max)",
    )
    ap.add_argument(
        "--coverage",
        action="store_true",
        help="also list which catalog risk families no task exercises",
    )
    args = ap.parse_args(argv)

    track = "effort" if args.by_effort else args.track
    runs, excluded = load_runs(args.runs, domain=args.domain, track=track)
    domains = sorted({r.domain for r in runs})
    if args.domain is None:
        if len(domains) > 1:
            print(
                f"error: runs span domains {domains}; rates are not comparable "
                f"across domains — pass --domain",
                file=sys.stderr,
            )
            return 2
        domain = domains[0] if domains else "geo"
    else:
        domain = args.domain

    from geocase.benchmark.cli import EmptySelectionError, select_tasks

    try:
        tasks = select_tasks(None, domain)
    except EmptySelectionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    render(runs, excluded, tasks, domain=domain, coverage=args.coverage, out=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
