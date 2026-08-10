"""The manual coding-agent protocol (Plan 15 Phase 5).

For agents that have no API and can only be driven by hand — Claude Code,
Cursor, Codex CLI. This is the track that reproduces the Step 0 condition, and
it is where the silent failures worth publishing live: the agent gets a
sandbox, runs its own code, verifies its own work, and still ships a plausible
wrong answer.

Two commands:

``manual prepare --out DIR``
    Builds the workdir — sandbox venv, ``generated/``, per-task scratch
    directories — and renders every prompt with *that directory's* absolute
    paths. This is the payoff from the Phase 1 templating: the same prompts,
    new paths, reproducing the Step 0 condition anywhere.

``manual ingest --dir DIR --model-id ... --protocol claude-code --trial N``
    Grades what the sessions produced and writes or extends the run record.

Between the two, the human runs one **fresh** agent session per task: cwd set
to the workdir, no repository access, no other context, prompt pasted verbatim,
run to ``DONE``, session closed. One task per session, order shuffled.
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from geocase.benchmark.grading import grade_in_subprocess
from geocase.benchmark.prompts import render_prompt
from geocase.benchmark.registry import all_tasks
from geocase.benchmark.runner.sandbox import REQUIREMENTS, ensure_sandbox

# How the loop was driven. Recorded per run so tracks are never silently
# mixed (Plan 15, trap 6).
PROTOCOLS = frozenset({"claude-code", "cursor", "codex-cli", "text-loop"})

MANIFEST = "manifest.json"


class ManualRunError(RuntimeError):
    pass


@dataclass
class PreparedWorkdir:
    workdir: Path
    python: Path | None
    prompts: dict[str, Path]
    order: list[str]


def shuffled_task_order(seed: int | None = None) -> list[str]:
    """Task order for the sessions. Shuffled so that fatigue, rate limits or
    a mid-run abort do not correlate with task identity; seeded so a run can
    be described exactly in the write-up."""
    names = [t.name for t in all_tasks()]
    random.Random(seed).shuffle(names)
    return names


def prepare(
    workdir: Path,
    *,
    create_venv: bool = True,
    seed: int | None = None,
    requirements: Path = REQUIREMENTS,
) -> PreparedWorkdir:
    """Build the agent workdir. Safe to re-run: never deletes generated work."""
    workdir = workdir.expanduser().resolve()
    (workdir / "generated").mkdir(parents=True, exist_ok=True)
    (workdir / "prompts").mkdir(exist_ok=True)

    python: Path | None = None
    if create_venv:
        python = ensure_sandbox(workdir, requirements)
    interpreter = python or (workdir / "venv" / "bin" / "python")

    prompts: dict[str, Path] = {}
    hashes: dict[str, str] = {}
    for task in all_tasks():
        (workdir / f"scratch_{task.name}").mkdir(exist_ok=True)
        text = render_prompt(task, workdir=workdir, python=interpreter)
        path = workdir / "prompts" / f"{task.name}.md"
        path.write_text(text)
        prompts[task.name] = path
        hashes[task.name] = hashlib.sha256(text.encode()).hexdigest()

    order = shuffled_task_order(seed)
    (workdir / MANIFEST).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "workdir": str(workdir),
                "sandbox_requirements_sha256": _sha256_file(requirements),
                "prompt_sha256": hashes,
                "order": order,
                "seed": seed,
            },
            indent=2,
        )
    )
    return PreparedWorkdir(workdir=workdir, python=python, prompts=prompts, order=order)


def ingest(
    workdir: Path,
    *,
    out_root: Path,
    model_id: str,
    label: str,
    protocol: str,
    trial: int,
    date: str,
    python: Path | None = None,
) -> dict[str, Any]:
    """Grade a completed session set and write (or extend) the run record."""
    if protocol not in PROTOCOLS:
        raise ManualRunError(
            f"unknown protocol {protocol!r}; expected one of {sorted(PROTOCOLS)}"
        )
    workdir = Path(workdir).expanduser().resolve()
    manifest_path = workdir / MANIFEST
    if not manifest_path.is_file():
        raise ManualRunError(
            f"no {MANIFEST} in {workdir} — run `manual prepare --out {workdir}` first"
        )
    manifest = json.loads(manifest_path.read_text())

    gen_dir = workdir / "generated"
    # Model-generated code is untrusted input: grade it in a child interpreter,
    # never by importing it here (Plan 15, trap 5). The sandbox venv lacks
    # geocase itself, so grading uses this interpreter unless told otherwise.
    outcomes = (
        grade_in_subprocess(gen_dir, python=python)
        if python is not None
        else grade_in_subprocess(gen_dir)
    )

    run_id = f"{date}_{_slug(model_id)}_agentic-manual"
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    record = _load_or_init_record(
        run_dir / "run.json",
        run_id=run_id,
        date=date,
        model_id=model_id,
        label=label,
        protocol=protocol,
        manifest=manifest,
    )

    for outcome in outcomes:
        rel = _copy_module(gen_dir, run_dir, outcome.task, trial)
        entry: dict[str, Any] = {
            "trial": trial,
            "module": rel,
            "module_sha256": (_sha256_file(run_dir / rel) if rel else None),
            "outcome": outcome.outcome,
            "checks": [
                {
                    "check": c.check,
                    "kind": c.kind.value if c.kind else None,
                    "status": c.status.value,
                    "detail": c.detail,
                }
                for c in outcome.checks
            ],
            "turns": None,
            "usage": None,
        }
        trials = record["tasks"].setdefault(outcome.task, {"trials": []})["trials"]
        # Re-ingesting the same trial replaces it rather than duplicating.
        trials[:] = [t for t in trials if t["trial"] != trial] + [entry]
        trials.sort(key=lambda t: t["trial"])

    record["config"]["trials"] = max(
        (t["trial"] for task in record["tasks"].values() for t in task["trials"]),
        default=trial,
    )
    (run_dir / "run.json").write_text(json.dumps(record, indent=2))
    return record


# ---------------------------------------------------------------- helpers


def _slug(model_id: str) -> str:
    import re

    return re.sub(r"[^a-z0-9.-]+", "-", model_id.lower())


def _sha256_file(path: Path) -> str | None:
    if not Path(path).is_file():
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _copy_module(gen_dir: Path, run_dir: Path, task: str, trial: int) -> str | None:
    from geocase.benchmark.registry import get_task

    src = gen_dir / get_task(task).module
    if not src.is_file():
        return None
    rel = Path("generated") / f"trial{trial}" / src.name
    dst = run_dir / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(rel)


def _load_or_init_record(
    path: Path,
    *,
    run_id: str,
    date: str,
    model_id: str,
    label: str,
    protocol: str,
    manifest: dict,
) -> dict[str, Any]:
    if path.is_file():
        record: dict[str, Any] = json.loads(path.read_text())
        if record.get("protocol") != protocol:
            raise ManualRunError(
                f"{path} was recorded with protocol {record.get('protocol')!r}; "
                f"refusing to mix in {protocol!r} (Plan 15, trap 6)"
            )
        return record

    from geocase.benchmark.runner.sandbox import REQUIREMENTS as REQ

    return {
        "schema_version": 2,
        "run_id": run_id,
        "date": date,
        "model": {"id": model_id, "label": label, "provider": "manual-cli"},
        "track": "agentic-manual",
        "protocol": protocol,
        "runner": {"name": "geocase-benchmark", "version": "2.0.0.dev0"},
        "config": {
            "trials": 0,
            "temperature": None,
            "max_turns": None,
            "variant_seed": manifest.get("seed"),
            "sandbox_requirements_sha256": manifest.get("sandbox_requirements_sha256")
            or _sha256_file(REQ),
            "prompt_sha256": manifest.get("prompt_sha256", {}),
        },
        "cost_usd": None,
        "tasks": {},
    }
