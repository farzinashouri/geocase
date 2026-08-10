"""Contamination probe prompts (Plan 16 Phase 0).

A probe asks an open question about a task's contract with no mention of any
edge case, and records whether the model names the trap unprompted. Probes are
optional per task and live at ``tasks/<name>/probe.md``; they are hashed like
any other prompt so a probe result is attributable to the exact question asked.

The probe deliberately carries no {workdir}/{python} scaffolding: it is not a
benchmark call, must be issued in a separate session, and asks for prose rather
than code.
"""

from __future__ import annotations

from geocase.benchmark.registry import TaskMeta

PROBE_FILE = "probe.md"


def has_probe(task: TaskMeta) -> bool:
    return (task.directory / PROBE_FILE).is_file()


def probe_prompt(task: TaskMeta) -> str:
    path = task.directory / PROBE_FILE
    if not path.is_file():
        raise FileNotFoundError(f"{task.name} has no {PROBE_FILE}")
    return path.read_text()


def tasks_with_probes(tasks: list[TaskMeta]) -> list[TaskMeta]:
    return [t for t in tasks if has_probe(t)]
