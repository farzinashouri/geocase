"""Review probe replies and set ``named_trap`` by hand (Plan 16, U7).

Prints one reply at a time with its task's trap category, then writes your
verdict back into the probe file. Deliberately manual: a model can describe a
trap without ever using its name, so no string match can stand in for reading.

    python scripts/review_probes.py                 # every unreviewed reply
    python scripts/review_probes.py --task buffer_m # one task
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from geocase.benchmark.registry import get_task


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="review_probes")
    ap.add_argument("--dir", type=Path, default=Path("results/probes"))
    ap.add_argument("--task", default=None, help="review one task only")
    ap.add_argument(
        "--all", action="store_true", help="include replies already reviewed"
    )
    args = ap.parse_args(argv)

    files = sorted(glob.glob(str(args.dir / "*.json")))
    if not files:
        print(f"no probe files in {args.dir}", file=sys.stderr)
        return 2

    reviewed = 0
    for path in files:
        data = json.loads(Path(path).read_text())
        changed = False
        for probe in data["probes"]:
            if args.task and probe["task"] != args.task:
                continue
            if probe["named_trap"] is not None and not args.all:
                continue
            trap = get_task(probe["task"]).trap_category
            print("=" * 72)
            print(f"model: {data['model']['id']}")
            print(f"task:  {probe['task']}   TRAP CATEGORY: {trap}")
            print("=" * 72)
            print(probe["reply"])
            print("-" * 72)
            print(f"Did it name the '{trap}' trap unprompted?")
            answer = input("  [y]es / [n]o / [s]kip / [q]uit: ").strip().lower()
            if answer.startswith("q"):
                if changed:
                    Path(path).write_text(json.dumps(data, indent=2))
                print(f"\nstopped; {reviewed} reviewed")
                return 0
            if answer.startswith("s"):
                continue
            probe["named_trap"] = answer.startswith("y")
            changed = True
            reviewed += 1
        if changed:
            Path(path).write_text(json.dumps(data, indent=2))
            print(f"saved {path}")

    print(f"\n{reviewed} reviewed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
