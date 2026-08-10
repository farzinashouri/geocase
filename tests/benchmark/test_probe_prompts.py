"""Contamination probe prompts (Plan 16 Phase 0).

A probe asks an open question about the task's contract and must not itself
name the trap — a probe that hints is worthless, because a model repeating the
hint back tells you nothing about what it already knew.
"""

import pytest

from geocase.benchmark.registry import all_tasks, get_task
from geocase.benchmark.runner.probe import has_probe, probe_prompt, tasks_with_probes

PROBED = [t for t in all_tasks() if has_probe(t)]


def test_every_stdlib_task_has_a_probe():
    """Phase 0 decides the stdlib slate, so none of it ships unprobed."""
    missing = [t.name for t in all_tasks() if t.domain == "stdlib" and not has_probe(t)]
    assert not missing, f"no probe.md for {missing}"


@pytest.mark.parametrize("task", PROBED, ids=lambda t: t.name)
def test_probe_asks_for_prose_not_code(task):
    text = probe_prompt(task)
    assert "pitfalls" in text.lower()
    assert "do not write code" in text.lower()


@pytest.mark.parametrize("task", PROBED, ids=lambda t: t.name)
def test_probe_carries_no_workdir_scaffolding(task):
    """A probe is not a benchmark call: no paths, no interpreter, no DONE."""
    text = probe_prompt(task)
    for placeholder in ("{workdir}", "{python}", "{module_path}", "{scratch_dir}"):
        assert placeholder not in text
    assert "DONE" not in text


@pytest.mark.parametrize("task", PROBED, ids=lambda t: t.name)
def test_probe_never_names_its_own_trap(task):
    """The probe must not supply the answer it is measuring."""
    text = probe_prompt(task).lower()
    assert task.trap_category.replace("-", " ") not in text
    banned = ("geocase", "benchmark", "trap", "edge case", "gotcha")
    for word in banned:
        assert word not in text, f"{task.name} probe leaks {word!r}"


def test_probe_prompt_missing_file_is_an_error():
    unprobed = next((t for t in all_tasks() if not has_probe(t)), None)
    if unprobed is None:
        pytest.skip("every task has a probe")
    with pytest.raises(FileNotFoundError):
        probe_prompt(unprobed)


def test_tasks_with_probes_filters():
    assert tasks_with_probes([get_task("sample_variance")]) == [
        get_task("sample_variance")
    ]
