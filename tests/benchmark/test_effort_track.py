"""Effort as a config axis, and the provenance that keeps it separate.

Plan 45 Phases 3 and 4. Two things are pinned here:

* one model carrying ``effort: [low, max]`` becomes two arms in **distinct**
  run directories — collide them and ``--resume`` skips the second as already
  done, which is a silent wrong result rather than an error;
* an effort run's ``run.json`` says, in the record itself, that it is not a
  bare completion. Without those markers a 15-arm effort table eventually gets
  read beside OpenRouter bare numbers and something false is concluded.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from geocase.benchmark.registry import all_tasks
from geocase.benchmark.runner.orchestrator import (
    _models_for_track,
    expand_effort_arms,
    run_bare_track,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _geo_tasks():
    return [t for t in all_tasks() if t.domain == "geo"]


# ------------------------------------------------------------- 3.1 expansion


def test_effort_list_expands_to_one_arm_per_level():
    models = [
        {"id": "claude-haiku-4-5", "label": "Haiku", "effort": ["low", "max"]},
        {"id": "claude-opus-5", "label": "Opus"},
    ]
    arms = expand_effort_arms(models)
    assert [(a["id"], a.get("effort")) for a in arms] == [
        ("claude-haiku-4-5", "low"),
        ("claude-haiku-4-5", "max"),
        ("claude-opus-5", None),
    ]
    # The source dicts are untouched: expansion must not mutate the config.
    assert models[0]["effort"] == ["low", "max"]


def test_expansion_rejects_an_unknown_effort_level():
    with pytest.raises(ValueError, match="turbo"):
        expand_effort_arms([{"id": "m", "effort": ["low", "turbo"]}])


def test_two_efforts_of_one_model_get_distinct_run_dirs(tmp_path, monkeypatch):
    """The collision that would make --resume skip the second arm."""
    tasks = _geo_tasks()[:2]
    seen = []

    def fake_run_bare_task(client, model_id, task, **kwargs):
        from geocase.benchmark.runner.bare import BareResult

        seen.append((model_id, client.effort, task.name))
        return BareResult(task.name, "```python\nx=1\n```", "x=1", None, {})

    _patch_runner(monkeypatch, fake_run_bare_task)
    run_bare_track(_effort_config(), out_root=tmp_path, tasks=tasks, track="effort")

    dirs = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
    assert len(dirs) == 2, f"efforts collided into one run dir: {dirs}"
    # The full tail, not just the level: a doubled `_effort_effort-low` also
    # ends in "_effort-low", so a suffix check alone would pass on a bad name.
    assert [d.split("_", 1)[1] for d in dirs] == [
        "claude-haiku-4-5_effort-low",
        "claude-haiku-4-5_effort-max",
    ]
    assert len(seen) == 2 * len(tasks)
    assert {effort for _, effort, _ in seen} == {"low", "max"}


def test_progress_lines_name_the_effort_arm(tmp_path, monkeypatch, capsys):
    """Two arms of one model print as `id @level`, never as a bare id.

    Without the level, a 2-arm run reads as trial 1..3 printed twice, and the
    operator cannot tell from the terminal which arm a verdict belongs to.
    """
    tasks = _geo_tasks()[:1]

    def fake_run_bare_task(client, model_id, task, **kwargs):
        from geocase.benchmark.runner.bare import BareResult

        return BareResult(task.name, "```python\nx=1\n```", "x=1", None, {})

    _patch_runner(monkeypatch, fake_run_bare_task)
    run_bare_track(_effort_config(), out_root=tmp_path, tasks=tasks, track="effort")

    out = capsys.readouterr().out
    for level in ("low", "max"):
        assert (
            f"claude-haiku-4-5 @{level} trial 1 {tasks[0].name}: code received" in out
        )
        assert f"grading claude-haiku-4-5 @{level} trial 1 ..." in out
        assert f"claude-haiku-4-5 @{level} trial 1: " in out
    assert "claude-haiku-4-5 trial 1" not in out


# ------------------------------------------------------------ 4.1 provenance


def test_effort_run_record_carries_the_full_provenance(tmp_path, monkeypatch):
    tasks = _geo_tasks()[:1]

    def fake_run_bare_task(client, model_id, task, **kwargs):
        from geocase.benchmark.runner.bare import BareResult

        return BareResult(
            task.name, "```python\nx=1\n```", "x=1", None, {"thinking_tokens": 46}
        )

    _patch_runner(monkeypatch, fake_run_bare_task)
    run_bare_track(_effort_config(), out_root=tmp_path, tasks=tasks, track="effort")

    run_dir = next(p for p in tmp_path.iterdir() if p.name.endswith("_effort-low"))
    record = json.loads((run_dir / "run.json").read_text())
    assert record["track"] == "effort"
    assert record["model"]["provider"] == "claude-cli"
    assert record["protocol"] == "claude-code"
    assert record["effort"] == "low"
    assert record["harness_version"].startswith("claude-cli/")
    # The marker the whole phase exists for.
    assert record["preamble"] == "claude-code-harness"
    # No spend figure is recorded: list prices are not billed on a seat.
    assert record["cost_usd"] is None

    meta = json.loads(
        (run_dir / "generated" / "trial1" / f"{tasks[0].name}.meta.json").read_text()
    )
    assert meta["track"] == "effort"
    assert meta["effort"] == "low"
    assert meta["preamble"] == "claude-code-harness"
    assert meta["cost_usd"] is None


def test_bare_defaults_are_unchanged_by_the_new_parameters(tmp_path):
    """``write_bare_record`` keeps today's literals when nothing is passed."""
    from geocase.benchmark.runner.record import write_bare_record

    record = write_bare_record(
        tmp_path,
        model={"id": "a/model", "label": "A"},
        trials=1,
        date="2026-09-10",
        config={"defaults": {"temperature": 0.2}},
        outcomes_by_trial={},
        cost_usd=0.0,
    )
    assert record["track"] == "bare"
    assert record["protocol"] == "openrouter-chat"
    assert record["model"]["provider"] == "openrouter"
    # Effort-only fields are absent from a bare record, not present-and-null:
    # a null `preamble` would read as "checked, none", which is a claim.
    assert "effort" not in record
    assert "preamble" not in record
    assert "harness_version" not in record


def test_backfill_reads_effort_provenance_from_the_metas(tmp_path):
    """Backfilling an effort run must not stamp it as a bare one.

    The orchestrator writes track/protocol/effort/harness_version/preamble
    into every meta, so a rebuilt record can carry them truthfully; ``cost_usd``
    stays ``None`` because no seat call is billed.
    """
    from geocase.benchmark.runner.record import backfill_bare_record

    gen = tmp_path / "generated" / "trial1"
    gen.mkdir(parents=True)
    (gen / "area_m2.meta.json").write_text(
        json.dumps(
            {
                "task": "area_m2",
                "model": "claude-haiku-4-5",
                "trial": 1,
                "track": "effort",
                "protocol": "claude-code",
                "effort": "low",
                "harness_version": "claude-cli/2.1.263",
                "preamble": "claude-code-harness",
                "cost_usd": None,
            }
        )
    )
    (gen / "graded.json").write_text("[]")

    record = backfill_bare_record(tmp_path)
    assert record["track"] == "effort"
    assert record["protocol"] == "claude-code"
    assert record["model"]["provider"] == "claude-cli"
    assert record["effort"] == "low"
    assert record["harness_version"] == "claude-cli/2.1.263"
    assert record["preamble"] == "claude-code-harness"
    assert record["cost_usd"] is None


# --------------------------------------------------- 4.1 committed-run pin


def _committed_runs() -> list[Path]:
    runs = REPO_ROOT / "results" / "runs"
    if not runs.is_dir():
        return []
    return sorted(p for p in runs.iterdir() if (p / "run.json").is_file())


@pytest.mark.parametrize("run_dir", _committed_runs(), ids=lambda p: p.name)
def test_committed_records_regenerate_byte_identically(run_dir: Path):
    """Every existing ``run.json`` rebuilds unchanged under the new defaults.

    ``module_sha256`` is recorded provenance and these trees are ruff-excluded
    to stay byte-stable; parameterising ``write_bare_record`` must not move a
    single byte of them. Compared as text, not by eye.

    Rebuilt through ``write_bare_record`` with the record's own inputs rather
    than through ``backfill_bare_record``: backfill reconstructs a record from
    the metas alone and cannot recover ``model.label``, which is a property of
    that function and not of the shape under test here.
    """
    from geocase.benchmark.runner.record import write_bare_record
    from geocase.benchmark.taxonomy import TrialOutcome

    before = (run_dir / "run.json").read_text()
    recorded = json.loads(before)
    outcomes_by_trial = {
        int(p.parent.name.removeprefix("trial")): [
            TrialOutcome.model_validate(o) for o in json.loads(p.read_text())
        ]
        for p in sorted((run_dir / "generated").glob("trial*/graded.json"))
    }
    try:
        write_bare_record(
            run_dir,
            model=recorded["model"],
            trials=recorded["config"]["trials"],
            date=recorded["date"],
            config={"defaults": {"temperature": recorded["config"]["temperature"]}},
            outcomes_by_trial=outcomes_by_trial,
            cost_usd=recorded["cost_usd"],
            domain=recorded["domain"],
            provider=recorded["model"]["provider"],
            track=recorded["track"],
            protocol=recorded["protocol"],
            effort=recorded.get("effort"),
            harness_version=recorded.get("harness_version"),
            preamble=recorded.get("preamble"),
        )
        after = (run_dir / "run.json").read_text()
    finally:
        (run_dir / "run.json").write_text(before)
    assert after == before, (
        f"{run_dir.name}/run.json changed on regeneration — the record shape "
        f"moved under a committed run"
    )


# ------------------------------------------------------------------ config


def test_shipped_effort_config_is_well_formed():
    config = yaml.safe_load(
        (REPO_ROOT / "configs" / "models-claude-effort.yaml").read_text()
    )
    models = _models_for_track(config, "effort")
    assert models, "no models declare the effort track"
    arms = expand_effort_arms(models)
    assert len(arms) == len(models) * 5
    for model in models:
        assert model["provider"] == "claude-cli"
    # A dollar ceiling of 0 on a track that never reports a cost: the abort
    # can only fire if something starts reporting spend, which is the point.
    assert config["budget"]["max_usd_total"] == 0.0
    assert config["defaults"]["temperature"] is None


# ------------------------------------------------------------------ helpers


def _effort_config() -> dict:
    return {
        "defaults": {"trials": 1, "temperature": None},
        "budget": {"max_usd_total": 0.0},
        "models": [
            {
                "id": "claude-haiku-4-5",
                "label": "Haiku 4.5",
                "tracks": ["effort"],
                "provider": "claude-cli",
                "effort": ["low", "max"],
            }
        ],
    }


class _FakeCli:
    def __init__(self, *, effort: str, **kwargs):
        self.effort = effort


def _patch_runner(monkeypatch, fake_run_bare_task) -> None:
    monkeypatch.setattr(
        "geocase.benchmark.runner.bare.run_bare_task", fake_run_bare_task
    )
    monkeypatch.setattr(
        "geocase.benchmark.runner.orchestrator.grade_in_subprocess",
        lambda d, tasks=None: [],
    )
    monkeypatch.setattr("geocase.benchmark.runner.claude_cli.ClaudeCliClient", _FakeCli)
