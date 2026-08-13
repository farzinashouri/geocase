"""Contamination probe (Plan 16 Phase 0).

Asks each model, in a session entirely separate from any benchmark run, an
open question about a task's contract — "what are the common pitfalls when
implementing X?" — with no mention of any edge case. If a model names the trap
unprompted, a near-zero silent rate on that task measures recall rather than
the phenomenon this benchmark exists to measure.

The interesting outcome is the *opposite* one: a model that names the trap and
still falls into it while self-verifying. That is the knowing-but-not-applying
finding, and it is the claim most resistant to "the benchmark just tests
obscure knowledge."

``named_trap`` is deliberately left ``null`` here and set by human review
(U7). String matching cannot do this job — a model can describe the
antimeridian problem without ever using the word.

    python scripts/contamination_probe.py --config configs/models-free.yaml --dry-run
    python scripts/contamination_probe.py --config configs/models-free.yaml
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import yaml

from geocase.benchmark.registry import TaskMeta, all_tasks
from geocase.benchmark.runner.policy import add_pacing_args, policy_from_args
from geocase.benchmark.runner.probe import probe_prompt, tasks_with_probes

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "results" / "probes"


def _slug(model_id: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", model_id.lower())


def _select(names: list[str] | None, domain: str | None) -> list[TaskMeta]:
    tasks = tasks_with_probes(all_tasks())
    if domain:
        tasks = [t for t in tasks if t.domain == domain]
    if names:
        wanted = set(names)
        tasks = [t for t in tasks if t.name in wanted]
    return tasks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="contamination_probe")
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tasks", nargs="*", default=None)
    ap.add_argument("--domain", default=None)
    ap.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="seconds between probes; free-tier quotas are per-minute too",
    )
    ap.add_argument(
        "--give-up-after",
        type=int,
        default=3,
        help="consecutive failures before skipping the rest of a model",
    )
    ap.add_argument("--dry-run", action="store_true")
    # Shared with `geocase.benchmark run` so the two cannot drift (Plan 17 §1.4).
    add_pacing_args(ap)
    args = ap.parse_args(argv)
    # One prose completion is a few seconds' work. Anything slower is a
    # rate-limited or stalling model, and across 156 calls the right response
    # is to fail that task fast and let --give-up-after skip the model.
    if args.task_budget is None:
        args.task_budget = 20.0

    config = yaml.safe_load(args.config.read_text())
    models = [m for m in config.get("models", []) if "bare" in m.get("tracks", [])]
    tasks = _select(args.tasks, args.domain)

    if not tasks:
        print("no tasks with a probe.md matched the selection", file=sys.stderr)
        return 2
    if not models:
        print(f"no bare-track models in {args.config}", file=sys.stderr)
        return 2

    print(
        f"{len(models)} models x {len(tasks)} probed tasks = "
        f"{len(models) * len(tasks)} completions"
    )
    if args.dry_run:
        for t in tasks:
            print(f"  {t.domain:<7} {t.name}")
        return 0

    pacing = policy_from_args(args, config)
    print(pacing.describe(), file=sys.stderr)
    client = pacing.build_client()
    date = dt.date.today().isoformat()
    args.out.mkdir(parents=True, exist_ok=True)

    landed = 0
    for model in models:
        path = args.out / f"{date}_{_slug(model['id'])}.json"
        # Resume-friendly: a rate-limited probe run is re-runnable without
        # re-asking anything already recorded.
        records: dict[str, dict] = {}
        if path.is_file():
            records = {r["task"]: r for r in json.loads(path.read_text())["probes"]}

        # Resumed probes count as landed: a re-run that finds everything
        # already on disk has nothing to do and is not a failure.
        landed += len(records)
        consecutive_failures = 0
        for i, task in enumerate(tasks):
            if task.name in records:
                continue
            # Pace the requests. Free-tier quotas are per-minute as well as
            # per-day, and firing 26 completions back to back is the surest way
            # to spend the whole run inside the retry backoff.
            if i and args.delay:
                time.sleep(args.delay)
            prompt = probe_prompt(task)
            # Printed before the call, not after: a run that is merely slow and
            # one that is wedged are otherwise indistinguishable from outside.
            print(f"{model['id']} {task.name}: asking ...", flush=True, file=sys.stderr)
            try:
                reply = client.chat(model["id"], [{"role": "user", "content": prompt}])
            except Exception as exc:  # noqa: BLE001 - one probe must not end the run
                print(f"{model['id']} {task.name}: FAILED ({exc})", file=sys.stderr)
                consecutive_failures += 1
                if consecutive_failures >= args.give_up_after:
                    # A model whose quota is exhausted (or whose id is stale)
                    # fails every remaining task identically. Stop and let the
                    # operator re-run later; resume keeps what did land.
                    print(
                        f"{model['id']}: {consecutive_failures} consecutive "
                        f"failures — skipping the rest of this model",
                        file=sys.stderr,
                    )
                    break
                continue
            consecutive_failures = 0
            records[task.name] = {
                "task": task.name,
                "domain": task.domain,
                "probe_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                # Set by hand in review (U7). Never inferred by string match.
                "named_trap": None,
                "reply": reply.content,
            }
            print(f"{model['id']} {task.name}: probed")
            landed += 1
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "date": date,
                        "model": {"id": model["id"], "label": model.get("label")},
                        "probes": [records[t.name] for t in tasks if t.name in records],
                    },
                    indent=2,
                )
            )
        # Inside the loop and conditional on the file: printing "wrote {path}"
        # unconditionally meant three models reported success on 2026-08-11
        # with nothing on disk — a silent failure in the silent-failure
        # benchmark's own tooling.
        if path.is_file():
            print(f"wrote {path} ({len(records)} probe(s))")
        else:
            print(f"{model['id']}: NO probes landed — nothing written", file=sys.stderr)

    if not landed:
        print(
            "NO probes landed — nothing written. Every request failed; check "
            "the account's rate limits and re-run (resume keeps what lands).",
            file=sys.stderr,
        )
        return 1

    print(
        "\nU7: review every reply and set `named_trap` true/false by hand. "
        "A null anywhere means the probe is not yet usable as evidence."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
