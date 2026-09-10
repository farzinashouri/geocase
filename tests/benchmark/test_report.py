"""``python -m geocase.benchmark report`` (Plan 46 §2.2).

Two synthetic runs on disk, in the schema v2 ``run.json`` shape the bare and
manual tracks both write. The report is computed from the ``checks`` already
stored there — nothing is written back, so Plan 45's byte-identical
regeneration requirement is untouched.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from geocase.benchmark.registry import get_task
from geocase.benchmark.runner import report as report_mod
from geocase.benchmark.runner.report import (
    build_matrix,
    category_rates,
    load_runs,
    reproducible_silent,
    wilson_interval,
)

# -------------------------------------------------------------- fixtures


def _checks(control: str, edge: str) -> list[dict]:
    return [
        {"check": "ctl", "kind": "control", "status": control, "detail": ""},
        {"check": "edge", "kind": "edge", "status": edge, "detail": ""},
    ]


CORRECT = _checks("PASS", "PASS")
TRAPPED = _checks("PASS", "SILENT")
BROKEN = _checks("SILENT", "PASS")
LOUD = _checks("PASS", "LOUD")
MISSING = [{"check": "import", "kind": None, "status": "MISSING", "detail": ""}]

_VERDICT = {"PASS": "CORRECT", "SILENT": "SILENT", "LOUD": "LOUD", "MISSING": "MISSING"}


def _outcome(checks: list[dict]) -> str:
    statuses = {c["status"] for c in checks}
    for s in ("MISSING", "SILENT", "LOUD"):
        if s in statuses:
            return _VERDICT[s]
    return "CORRECT"


def _write_run(
    root: Path,
    run_id: str,
    *,
    model_id: str,
    label: str,
    trials: dict[str, list[list[dict]]],
    publishable: bool = True,
    domain: str = "geo",
    track: str = "bare",
    extra: dict | None = None,
) -> Path:
    run_dir = root / run_id
    (run_dir / "generated" / "trial1").mkdir(parents=True)
    n_trials = max(len(v) for v in trials.values())
    record = {
        "schema_version": 2,
        "run_id": run_id,
        "date": run_id.split("_", 1)[0],
        "domain": domain,
        "model": {"id": model_id, "label": label, "provider": "openrouter"},
        "track": track,
        "protocol": "openrouter-chat",
        **(extra or {}),
        "runner": {"name": "geocase-benchmark", "version": "2.0.0.dev0"},
        "config": {"trials": n_trials, "temperature": None, "prompt_sha256": {}},
        "cost_usd": 0.0,
        "integrity": {
            "tasks_attempted": sum(len(v) for v in trials.values()),
            "api_failures": 0 if publishable else 1,
            "publishable": publishable,
        },
        "tasks": {
            task: {
                "trials": [
                    {
                        "trial": i + 1,
                        "module": None,
                        "module_sha256": None,
                        "outcome": _outcome(checks),
                        "checks": checks,
                        "turns": None,
                        "usage": None,
                        "status": None,
                    }
                    for i, checks in enumerate(per_trial)
                ]
            }
            for task, per_trial in trials.items()
        },
    }
    (run_dir / "run.json").write_text(json.dumps(record, indent=2))
    return run_dir


@pytest.fixture
def runs_root(tmp_path: Path) -> Path:
    # Run A: publishable, k=3. buffer_m trapped every trial; area_m2 flaky.
    _write_run(
        tmp_path,
        "2026-09-01_model-a_bare",
        model_id="org/model-a",
        label="Model A",
        trials={
            "area_m2": [CORRECT, TRAPPED, TRAPPED],
            "buffer_m": [TRAPPED, TRAPPED, TRAPPED],
            "length_m": [CORRECT, CORRECT, BROKEN],
            "utm_epsg_for": [LOUD, MISSING, CORRECT],
        },
    )
    # Run B: rate-limit damage. Must be excluded from every rate, by name.
    _write_run(
        tmp_path,
        "2026-09-02_model-b_bare",
        model_id="org/model-b",
        label="Model B",
        trials={"area_m2": [CORRECT], "buffer_m": [CORRECT]},
        publishable=False,
    )
    return tmp_path


TASKS = [get_task(n) for n in ("area_m2", "buffer_m", "length_m", "utm_epsg_for")]


# ------------------------------------------------------------- 2.2 tables


def test_unpublishable_runs_are_excluded_and_named(runs_root):
    runs, excluded = load_runs(runs_root, domain="geo")
    assert [r.run_id for r in runs] == ["2026-09-01_model-a_bare"]
    assert [e.run_id for e in excluded] == ["2026-09-02_model-b_bare"]
    assert "publishable" in excluded[0].reason


def test_matrix_cells_show_every_trial_side_by_side(runs_root):
    runs, _ = load_runs(runs_root, domain="geo")
    matrix = build_matrix(runs, TASKS)
    col = runs[0].column
    assert matrix["area_m2"][col] == ["C", "T", "T"]  # reads as one flaky task
    assert matrix["buffer_m"][col] == ["T", "T", "T"]  # reads as a defect
    assert matrix["length_m"][col] == ["C", "C", "B"]  # broken, not trapped
    assert matrix["utm_epsg_for"][col] == ["L", "M", "C"]
    # Model B contributes no column at all.
    assert all(set(cells) == {col} for cells in matrix.values())


def test_per_category_trapped_rates_carry_wilson_intervals(runs_root):
    runs, _ = load_runs(runs_root, domain="geo")
    rates = category_rates(runs, TASKS)
    col = runs[0].column
    # antimeridian: area_m2 (1 of 3 correct) + buffer_m (3 of 3 trapped)
    # = 5 trapped of 6 trials.
    anti = rates[col]["antimeridian"]
    assert (anti.trapped, anti.n) == (5, 6)
    lo, hi = wilson_interval(5, 6)
    assert (anti.low, anti.high) == pytest.approx((lo, hi))
    # units-degrees: length_m's one BROKEN trial is not a trapped trial.
    units = rates[col]["units-degrees"]
    assert (units.trapped, units.broken, units.n) == (0, 1, 3)


def test_reproducible_silent_needs_every_trial_trapped_at_k3(runs_root):
    runs, _ = load_runs(runs_root, domain="geo")
    repro = reproducible_silent(runs, TASKS)
    assert repro[runs[0].column] == ["buffer_m"]


def test_reproducible_silent_is_not_claimed_below_k3(tmp_path):
    _write_run(
        tmp_path,
        "2026-09-03_model-c_bare",
        model_id="org/model-c",
        label="Model C",
        trials={"buffer_m": [TRAPPED, TRAPPED]},
    )
    runs, _ = load_runs(tmp_path, domain="geo")
    assert reproducible_silent(runs, TASKS) == {runs[0].column: []}


# ------------------------------------------------------------ 2.2 wilson


def test_wilson_interval_reference_values():
    lo, hi = wilson_interval(5, 20)
    assert (lo, hi) == pytest.approx((0.1122, 0.4687), abs=5e-4)
    assert wilson_interval(0, 20) == pytest.approx((0.0, 0.1611), abs=5e-4)
    assert wilson_interval(20, 20) == pytest.approx((0.8389, 1.0), abs=5e-4)
    assert wilson_interval(0, 0) == (0.0, 1.0)


# ------------------------------------------------------- 2.2 comparability


def test_effort_columns_carry_the_preamble_marker(tmp_path):
    _write_run(
        tmp_path,
        "2026-09-04_claude-x_effort-low",
        model_id="claude-x",
        label="Claude X",
        trials={"buffer_m": [TRAPPED]},
        track="effort",
        extra={"effort": "low", "preamble": "claude-code-harness"},
    )
    runs, _ = load_runs(tmp_path, domain="geo")
    assert runs[0].column == "Claude X @low [claude-code-harness]"


def test_mixed_domains_are_refused_without_a_domain_filter(tmp_path, capsys):
    _write_run(
        tmp_path,
        "2026-09-05_m_bare",
        model_id="m",
        label="M",
        trials={"buffer_m": [TRAPPED]},
    )
    _write_run(
        tmp_path,
        "2026-09-05_m_bare_stdlib",
        model_id="m",
        label="M",
        trials={"parse_delimited": [TRAPPED]},
        domain="stdlib",
    )
    rc = report_mod.main(["--runs", str(tmp_path)])
    assert rc == 2
    assert "domain" in capsys.readouterr().err


def test_cli_prints_the_four_tables_and_the_exclusion(runs_root):
    out = io.StringIO()
    rc = report_mod.main(["--runs", str(runs_root), "--domain", "geo"], out=out)
    text = out.getvalue()
    assert rc == 0
    assert "TASK x MODEL" in text
    assert "PER TRAP CATEGORY" in text
    assert "REPRODUCIBLE SILENT" in text
    assert "EXCLUDED" in text and "2026-09-02_model-b_bare" in text
    assert "buffer_m" in text and "T T T" in text
    # No blended headline number.
    assert "overall" not in text.lower()


def test_cli_coverage_lists_risk_families_no_task_exercises(runs_root):
    out = io.StringIO()
    rc = report_mod.main(
        ["--runs", str(runs_root), "--domain", "geo", "--coverage"], out=out
    )
    text = out.getvalue()
    assert rc == 0
    assert "COVERAGE" in text
    for family in ("transform", "dtype", "precision"):
        assert family in text


def test_report_is_dispatched_from_the_cli(runs_root, capsys):
    from geocase.benchmark.cli import main

    rc = main(["report", "--runs", str(runs_root), "--domain", "geo"])
    assert rc == 0
    assert "TASK x MODEL" in capsys.readouterr().out
