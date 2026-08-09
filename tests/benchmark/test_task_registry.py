"""Registry contracts (Plan 15 Phase 1).

Every ``task.yaml`` must validate; declared checks must exactly match what the
grader emits; handbook citations must be machine-checkable (Plan 14, trap 8).
"""

import os
import re
from pathlib import Path

import pytest

from geocase.benchmark.grading import grade_module
from geocase.benchmark.prompts import render_prompt
from geocase.benchmark.registry import all_tasks, get_task, tasks_root
from geocase.benchmark.taxonomy import TRAP_CATEGORIES

STEP0_GENERATED = Path(__file__).parent / "agent_baseline" / "generated"

TASKS = all_tasks()


def test_discovers_all_task_packages():
    dirs = {p.name for p in tasks_root().iterdir() if (p / "task.yaml").exists()}
    assert {t.name for t in TASKS} == dirs
    assert len(TASKS) >= 10


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.name)
def test_task_metadata_is_coherent(task):
    assert task.schema_version == 1
    assert task.module == f"gen_{task.name}.py"
    assert task.function == task.name
    assert task.trap_category in TRAP_CATEGORIES
    assert task.origin in {"step0", "plan15"}
    assert task.checks, "a task must declare at least one check"
    kinds = {c.kind for c in task.checks}
    assert "control" in {k.value for k in kinds}, "every task needs a control check"
    assert "edge" in {k.value for k in kinds}, "every task needs an edge check"


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.name)
def test_handbook_id_shape(task):
    assert task.handbook_id is None or re.fullmatch(r"[A-Z]{3}-\d{4}", task.handbook_id)


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.name)
def test_prompt_renders_without_leftover_placeholders(task):
    text = render_prompt(
        task, workdir=Path("/work/dir"), python="/work/dir/venv/bin/python"
    )
    assert "{workdir}" not in text
    assert "{python}" not in text
    assert "{module_path}" not in text
    assert "{scratch_dir}" not in text
    assert f"/work/dir/generated/{task.module}" in text
    assert "DONE" in text


def test_get_task_roundtrip():
    for task in TASKS:
        assert get_task(task.name).name == task.name
    with pytest.raises(KeyError):
        get_task("no_such_task")


@pytest.mark.parametrize(
    "task", [t for t in TASKS if t.origin == "step0"], ids=lambda t: t.name
)
def test_declared_checks_match_grader_emissions(task):
    """Names and kinds in task.yaml are exactly what the grader emits, in order,
    when run against the committed Step 0 modules."""
    outcome = grade_module(task, STEP0_GENERATED)
    emitted = [(c.check, c.kind.value) for c in outcome.checks]
    declared = [(c.name, c.kind.value) for c in task.checks]
    assert emitted == declared


@pytest.mark.skipif(
    not os.environ.get("GEOCASE_STUDIES_PATH"),
    reason="GEOCASE_STUDIES_PATH not set (handbook lives on the author's machine)",
)
@pytest.mark.parametrize(
    "task", [t for t in TASKS if t.handbook_id], ids=lambda t: t.name
)
def test_handbook_id_resolves(task):
    root = Path(os.environ["GEOCASE_STUDIES_PATH"]).expanduser()
    pattern = re.compile(rf"^id:\s*{re.escape(task.handbook_id)}\s*$", re.MULTILINE)
    hits = [
        p for p in root.rglob("*.md") if pattern.search(p.read_text(errors="ignore"))
    ]
    assert hits, f"{task.handbook_id} does not resolve to any question file's id"
