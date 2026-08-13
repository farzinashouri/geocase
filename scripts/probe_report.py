"""Summarise contamination probes as a task x model matrix (Plan 16 Phase 0).

The matrix *is* the result. There is no aggregate score: a near-zero silent
rate on a task every model can describe is a different fact from one on a task
none can, and averaging the two throws away the only thing being measured.

    python scripts/probe_report.py
    python scripts/probe_report.py --domain stdlib
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from geocase.benchmark.registry import get_task

# named / not named / not yet reviewed
MARKS = {True: "KNOWS", False: "  -  ", None: "  ?  "}


def _rate(cells, tasks, model):
    """Fraction of this model's *reviewed* probes that named the trap."""
    vals = [cells.get((t, model)) for t in tasks]
    done = [v for v in vals if v is not None]
    if not done:
        return f"{'--':<13}"
    named = sum(done)
    return f"{named}/{len(done)} ({named / len(done):.0%})".ljust(13)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="probe_report")
    ap.add_argument("--dir", type=Path, default=Path("results/probes"))
    ap.add_argument("--domain", default=None)
    args = ap.parse_args(argv)

    files = sorted(glob.glob(str(args.dir / "*.json")))
    if not files:
        print(f"no probe files in {args.dir}", file=sys.stderr)
        return 2

    judged: set[tuple[str, str]] = set()
    models: list[str] = []
    cells: dict[tuple[str, str], bool | None] = {}
    tasks: list[str] = []
    for path in files:
        data = json.loads(Path(path).read_text())
        model = data["model"]["id"]
        if model not in models:
            models.append(model)
        for probe in data["probes"]:
            if args.domain and probe.get("domain") != args.domain:
                continue
            if probe["task"] not in tasks:
                tasks.append(probe["task"])
            cells[(probe["task"], model)] = probe["named_trap"]
            if probe.get("named_trap_source") == "judge":
                judged.add((probe["task"], model))

    if not tasks:
        print("no probes matched", file=sys.stderr)
        return 2
    tasks.sort()

    wid = max(len(t) for t in tasks) + 2
    short = [m.split("/")[-1].replace(":free", "")[:11] for m in models]
    print()
    print(f"{'task':<{wid}}{'trap':<18}" + "".join(f"{s:<13}" for s in short))
    print("-" * (wid + 18 + 13 * len(models)))
    for task in tasks:
        trap = get_task(task).trap_category
        # Lower case marks a machine-set flag: same verdict, weaker evidence.
        row = ""
        for m in models:
            mark = MARKS[cells.get((task, m))]
            row += f"{mark.lower() if (task, m) in judged else mark:<13}"
        print(f"{task:<{wid}}{trap:<18}{row}")

    # Per-model contamination rate: of the tasks this model was probed on and
    # reviewed, how many did it name unprompted? Well-defined and comparable
    # across models, because every model answers the same probe set.
    print()
    print(
        f"{'contamination rate':<{wid + 18}}"
        + "".join(_rate(cells, tasks, m) for m in models)
    )

    reviewed = [v for v in cells.values() if v is not None]
    pending = len(cells) - len(reviewed)
    print()
    print("KNOWS = named the trap unprompted;  -  = did not;  ? = not set")
    if judged:
        print(
            f"lower-case = set by an LLM judge, not a human ({len(judged)} of "
            f"{len(cells)}). Run judge_probes.py --measure-agreement to find "
            f"how often the judge matches human review."
        )
    if pending:
        print(f"\n{pending} reply(ies) still unreviewed — run scripts/review_probes.py")

    # Per-task, because that is the unit the selection rule acts on.
    flagged = [
        t
        for t in tasks
        if (vals := [cells.get((t, m)) for m in models])
        and all(v is True for v in vals if v is not None)
        and any(v is not None for v in vals)
    ]
    if flagged:
        print(
            "\nNamed by every model probed so far: "
            + ", ".join(flagged)
            + "\n  These measure recall unless the run shows models fall in anyway."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
