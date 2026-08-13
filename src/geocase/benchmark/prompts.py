"""Prompt rendering.

Templates carry ``{workdir}``, ``{python}``, ``{module_path}`` and
``{scratch_dir}`` placeholders; the committed Step 0 prompts hard-coded
absolute paths from the original session and could not be re-run elsewhere.
Placeholders are substituted by literal replacement, not ``str.format``, so
braces in task text (e.g. set literals) never need escaping.
"""

from __future__ import annotations

from pathlib import Path

from geocase.benchmark.registry import TaskMeta

PLACEHOLDERS = ("{workdir}", "{python}", "{module_path}", "{scratch_dir}")


def task_paragraph(task: TaskMeta) -> str:
    """The task statement alone, without the file/interpreter scaffolding —
    what the bare track sends, since there is no filesystem to save into."""
    text = task.prompt_template
    start = text.index("Task: ")
    end = text.index("\n\nRequirements:")
    return text[start:end].strip()


def render_prompt(task: TaskMeta, *, workdir: Path, python: str | Path) -> str:
    text = task.prompt_template
    values = {
        "{workdir}": str(workdir),
        "{python}": str(python),
        "{module_path}": str(workdir / "generated" / task.module),
        "{scratch_dir}": str(workdir / f"scratch_{task.name}"),
    }
    for placeholder, value in values.items():
        text = text.replace(placeholder, value)
    return text
