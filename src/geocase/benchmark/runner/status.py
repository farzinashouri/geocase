"""``python -m geocase.benchmark status`` (Plan 17 §2.2).

The command whose absence let every problem in Plan 17 go unnoticed: a probe
sweep that landed 25 of 160, two committed runs recording rate-limit damage as
model behaviour, and a run with no ``graded.json`` at all — none of it visible
without reading directories by hand.

Everything here is read off disk. There is no state file to fall out of sync
with what actually happened, and **the exit code is non-zero whenever a blocker
exists**, so this works as a pre-commit gate.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from geocase.benchmark.registry import TaskMeta


def _slug(model_id: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", model_id.lower())


@dataclass
class TrialStatus:
    name: str
    modules: int
    api_failures: int
    graded: bool
    graded_stale: bool


@dataclass
class RunStatus:
    run_dir: Path
    model_id: str
    trials: list[TrialStatus] = field(default_factory=list)
    has_record: bool = False
    publishable: bool | None = None

    @property
    def api_failures(self) -> int:
        return sum(t.api_failures for t in self.trials)


@dataclass
class ProbeStatus:
    path: Path
    model_id: str
    landed: int
    unreviewed: int


def _trial_status(trial_dir: Path) -> TrialStatus:
    modules = 0
    api_failures = 0
    for meta_path in sorted(trial_dir.glob("*.meta.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        modules += 1
        if meta.get("status") in ("api_failure", "timeout"):
            api_failures += 1
    graded_path = trial_dir / "graded.json"
    graded = graded_path.is_file()
    stale = False
    if graded:
        # A grading older than the newest generated module was computed against
        # code that has since changed; reporting it as current would be the
        # benchmark's own silent failure.
        newest = max((p.stat().st_mtime for p in trial_dir.glob("*.py")), default=0.0)
        stale = newest > graded_path.stat().st_mtime
    return TrialStatus(
        name=trial_dir.name,
        modules=modules,
        api_failures=api_failures,
        graded=graded,
        graded_stale=stale,
    )


def scan_runs(
    runs_root: Path, *, model_ids: list[str] | None = None
) -> list[RunStatus]:
    """Every run directory on disk, optionally filtered to a config's roster."""
    wanted = {_slug(m) for m in model_ids} if model_ids else None
    out: list[RunStatus] = []
    for run_dir in sorted(p for p in runs_root.glob("*") if p.is_dir()):
        gen_root = run_dir / "generated"
        if not gen_root.is_dir():
            continue
        record_path = run_dir / "run.json"
        model_id = run_dir.name
        publishable: bool | None = None
        if record_path.is_file():
            try:
                record = json.loads(record_path.read_text())
                model_id = record.get("model", {}).get("id", model_id)
                publishable = record.get("integrity", {}).get("publishable")
            except (OSError, ValueError):
                pass
        else:
            for meta_path in sorted(gen_root.glob("trial*/*.meta.json")):
                try:
                    model_id = json.loads(meta_path.read_text()).get("model", model_id)
                except (OSError, ValueError):
                    continue
                break
        if wanted is not None and _slug(model_id) not in wanted:
            continue
        out.append(
            RunStatus(
                run_dir=run_dir,
                model_id=model_id,
                trials=[
                    _trial_status(d)
                    for d in sorted(gen_root.glob("trial*"))
                    if d.is_dir()
                ],
                has_record=record_path.is_file(),
                publishable=publishable,
            )
        )
    return out


def scan_probes(
    probes_root: Path, *, model_ids: list[str] | None = None
) -> list[ProbeStatus]:
    wanted = {_slug(m) for m in model_ids} if model_ids else None
    out: list[ProbeStatus] = []
    for path in sorted(probes_root.glob("*.json")) if probes_root.is_dir() else []:
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        probes = data.get("probes") or []
        model_id = (data.get("model") or {}).get("id", path.stem)
        if wanted is not None and _slug(model_id) not in wanted:
            continue
        out.append(
            ProbeStatus(
                path=path,
                model_id=model_id,
                landed=len(probes),
                # `named_trap` is set by hand in review (U7). A null is not a
                # "false" — it means the probe is not yet usable as evidence.
                unreviewed=sum(1 for p in probes if p.get("named_trap") is None),
            )
        )
    return out


def report(
    runs: list[RunStatus],
    probes: list[ProbeStatus],
    *,
    tasks: list[TaskMeta] | None = None,
    out=sys.stdout,
) -> list[str]:
    """Print the status table; return the blocker lines (empty = all clear)."""
    n_tasks = len(tasks) if tasks else None
    blockers: list[str] = []

    print("PROBES", file=out)
    if not probes:
        print("  (none on disk)", file=out)
    for p in probes:
        print(
            f"  {p.model_id:<44} {p.landed:>3} landed, {p.unreviewed:>3} unreviewed",
            file=out,
        )
        if p.unreviewed:
            blockers.append(
                f"{p.model_id}: {p.unreviewed} probe reply(ies) have named_trap=null "
                f"— review by hand (U7): python scripts/review_probes.py {p.path}"
            )

    print("\nRUNS", file=out)
    if not runs:
        print("  (none on disk)", file=out)
    for r in runs:
        flag = (
            ""
            if r.publishable is None
            else ("  publishable" if r.publishable else "  NOT PUBLISHABLE")
        )
        print(f"  {r.run_dir.name}{flag}", file=out)
        for t in r.trials:
            of = f"/{n_tasks}" if n_tasks else ""
            grade = (
                "graded"
                if t.graded and not t.graded_stale
                else ("STALE grading" if t.graded_stale else "NOT GRADED")
            )
            fails = f", {t.api_failures} api_failure" if t.api_failures else ""
            print(
                f"    {t.name:<8} {t.modules:>3}{of} module(s){fails} — {grade}",
                file=out,
            )
            if not t.graded:
                blockers.append(f"{r.run_dir.name}/{t.name}: no graded.json")
            elif t.graded_stale:
                blockers.append(
                    f"{r.run_dir.name}/{t.name}: graded.json is older than its "
                    f"newest module — re-grade"
                )
            if n_tasks and t.modules < n_tasks:
                blockers.append(
                    f"{r.run_dir.name}/{t.name}: {t.modules} of {n_tasks} tasks "
                    f"attempted — run is incomplete"
                )
        if not r.has_record:
            blockers.append(f"{r.run_dir.name}: no run.json (backfill it)")
        if r.api_failures:
            blockers.append(
                f"{r.run_dir.name}: {r.api_failures} api_failure(s) — rate-limit "
                f"damage, not model behaviour. Do not publish a rate from this "
                f"run; re-run it under Plan 17 pacing."
            )

    print("\nBLOCKERS", file=out)
    if not blockers:
        print("  none", file=out)
    for b in blockers:
        print(f"  - {b}", file=out)
    return blockers


def main(argv: list[str] | None = None) -> int:
    import argparse

    import yaml

    ap = argparse.ArgumentParser(prog="geocase.benchmark status")
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--domain", default=None)
    ap.add_argument("--runs", type=Path, default=Path("results/runs"))
    ap.add_argument("--probes", type=Path, default=Path("results/probes"))
    args = ap.parse_args(argv)

    model_ids = None
    if args.config is not None:
        config = yaml.safe_load(args.config.read_text())
        model_ids = [m["id"] for m in config.get("models", [])]

    tasks = None
    if args.domain:
        from geocase.benchmark.cli import EmptySelectionError, select_tasks

        try:
            tasks = select_tasks(None, args.domain)
        except EmptySelectionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    blockers = report(
        scan_runs(args.runs, model_ids=model_ids),
        scan_probes(args.probes, model_ids=model_ids),
        tasks=tasks,
    )
    # Non-zero on any blocker: this is meant to be usable as a gate, and a
    # gate that always passes is not a gate.
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
