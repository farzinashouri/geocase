"""Domain mechanism contracts (Plan 16 Phases 1 and 3).

The instrument was always domain-agnostic; these pin the seams that make a
second domain expressible without disturbing the first.
"""

import subprocess
import sys

import pytest
import yaml
from pydantic import ValidationError

from geocase.benchmark.cli import EmptySelectionError, select_tasks
from geocase.benchmark.domains import DOMAINS, GEO_DEPS, get_domain
from geocase.benchmark.registry import TaskMeta, all_tasks, get_task
from geocase.benchmark.runner.bare import bare_prompt
from geocase.benchmark.runner.orchestrator import _run_dir_suffix, plan_run
from geocase.benchmark.taxonomy import (
    GEO_TRAP_CATEGORIES,
    TRAP_CATEGORIES,
    TRAP_CATEGORIES_BY_DOMAIN,
)


def _yaml(name):
    return yaml.safe_load((get_task(name).directory / "task.yaml").read_text())


# ------------------------------------------------------------- taxonomy


def test_trap_categories_alias_still_means_the_geo_vocabulary():
    assert TRAP_CATEGORIES is GEO_TRAP_CATEGORIES


def test_domain_vocabularies_are_disjoint():
    geo = TRAP_CATEGORIES_BY_DOMAIN["geo"]
    stdlib = TRAP_CATEGORIES_BY_DOMAIN["stdlib"]
    assert not (geo & stdlib), "a shared category would blur which domain a trap is in"


# ------------------------------------------------------------- registry


def test_task_yaml_rejects_unknown_keys():
    """extra="ignore" would drop a typo'd key silently — this repo's own topic."""
    data = _yaml("buffer_m") | {"domian": "stdlib"}
    with pytest.raises(ValidationError):
        TaskMeta.model_validate(data)


def test_trap_category_is_validated_against_its_own_domain():
    # A geo task must not be able to declare a numeric trap.
    data = _yaml("buffer_m") | {"trap_category": "cancellation"}
    with pytest.raises(ValidationError):
        TaskMeta.model_validate(data)
    # ...and the same category is fine once the domain agrees.
    TaskMeta.model_validate(data | {"domain": "stdlib"})


def test_unknown_domain_is_rejected():
    with pytest.raises(ValidationError):
        TaskMeta.model_validate(_yaml("buffer_m") | {"domain": "nosuchdomain"})


def test_geo_tasks_declare_no_domain_and_default_to_geo():
    for task in all_tasks():
        if task.domain != "geo":
            continue
        assert "domain" not in _yaml(task.name), (
            f"{task.name}: geo is the default; backfilling it costs an empty diff"
        )


# ------------------------------------------------------------- prompts


def test_geo_dependency_sentence_is_byte_identical_to_the_committed_one():
    """The one string the 51 committed prompt hashes depend on."""
    assert GEO_DEPS == (
        "You may use the standard library plus any of: shapely 2.1, "
        "pyproj 3.7, rasterio 1.4, numpy, scikit-learn."
    )
    assert f"- {GEO_DEPS}\n" in bare_prompt(get_task("buffer_m"))


def test_stdlib_bare_prompt_advertises_no_third_party_packages():
    text = bare_prompt(get_task("sample_variance"))
    for pkg in ("shapely", "pyproj", "rasterio", "numpy", "scikit-learn"):
        assert pkg not in text


def test_stdlib_sandbox_installs_nothing():
    assert get_domain("stdlib").packages == frozenset()


# ------------------------------------------------------------- selection


def test_select_tasks_intersects_names_and_domain():
    got = select_tasks(["buffer_m", "sample_variance"], "stdlib")
    assert [t.name for t in got] == ["sample_variance"]


def test_select_tasks_refuses_an_empty_selection():
    # Today's behaviour without this: "0 of 0 graded", exit 0 — a silent
    # failure in the benchmark's own tooling.
    with pytest.raises(EmptySelectionError):
        select_tasks(["nonexistent"], None)
    with pytest.raises(EmptySelectionError):
        select_tasks(None, "nosuchdomain")


def test_every_declared_domain_has_tasks():
    by_domain = {t.domain for t in all_tasks()}
    assert set(DOMAINS) == by_domain


# ------------------------------------------------------------- run path


def test_run_dir_keeps_the_committed_name_for_geo():
    assert _run_dir_suffix([t for t in all_tasks() if t.domain == "geo"]) == ""


def test_run_dir_is_suffixed_for_other_domains():
    assert (
        _run_dir_suffix([t for t in all_tasks() if t.domain == "stdlib"]) == "_stdlib"
    )


def test_mixed_domain_run_is_refused():
    with pytest.raises(ValueError, match="mixed-domain"):
        _run_dir_suffix(all_tasks())


def test_dry_run_call_count_follows_the_domain_filter():
    config = {
        "defaults": {"trials": 2},
        "budget": {"max_usd_total": 1.0},
        "models": [{"id": "a/x", "label": "A", "tracks": ["bare"]}],
    }
    tasks = select_tasks(None, "stdlib")
    assert plan_run(config, track="bare", tasks=tasks).calls == 2 * len(tasks)


# ------------------------------------------------------------- CLI exit codes


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "geocase.benchmark", *args],
        capture_output=True,
        text=True,
    )


def test_grade_exits_non_zero_on_an_unknown_domain(tmp_path):
    r = _cli("grade", "--generated", str(tmp_path), "--domain", "nosuchdomain")
    assert r.returncode != 0
    assert "nosuchdomain" in r.stderr


def test_grade_exits_non_zero_on_an_unknown_task(tmp_path):
    r = _cli("grade", "--generated", str(tmp_path), "--tasks", "nonexistent")
    assert r.returncode != 0


def test_manual_prepare_requires_a_domain(tmp_path):
    r = _cli("manual", "prepare", "--out", str(tmp_path / "lab"), "--no-venv")
    assert r.returncode != 0
    assert "--domain" in r.stderr
