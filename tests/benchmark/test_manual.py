"""Manual coding-agent protocol (Plan 15 Phase 5).

The prepare -> ingest round trip is exercised against a scripted fake agent
that writes correct modules, so the protocol is tested without driving a real
coding-agent CLI. Sandbox creation is skipped throughout (``--no-venv``):
building a venv takes minutes and is not what these tests are about.
"""

import json
import textwrap

import pytest

from geocase.benchmark.registry import all_tasks, get_task
from geocase.benchmark.runner.manual import (
    ManualRunError,
    ingest,
    prepare,
    shuffled_task_order,
)

GOOD_LENGTH_M = """
from pyproj import Geod
_GEOD = Geod(ellps="WGS84")

def length_m(line):
    return _GEOD.geometry_length(line)
"""

TRAPPED_WKT = """
def wkt_from_latlon(lat, lon):
    return f"POINT ({lat} {lon})"
"""


# ---------------------------------------------------------------- prepare


def test_prepare_builds_the_workdir_layout(tmp_path):
    workdir = tmp_path / "lab"
    plan = prepare(workdir, create_venv=False)

    assert (workdir / "generated").is_dir()
    for task in all_tasks():
        assert (workdir / f"scratch_{task.name}").is_dir()
        assert (workdir / "prompts" / f"{task.name}.md").is_file()
    assert plan.workdir == workdir


def test_prepare_renders_absolute_paths_of_this_workdir(tmp_path):
    workdir = tmp_path / "lab"
    prepare(workdir, create_venv=False)

    text = (workdir / "prompts" / "buffer_m.md").read_text()
    assert str(workdir) in text
    assert str(workdir / "generated" / "gen_buffer_m.py") in text
    assert str(workdir / "scratch_buffer_m") in text
    assert "{workdir}" not in text


def test_prepare_writes_a_manifest_with_prompt_hashes(tmp_path):
    workdir = tmp_path / "lab"
    prepare(workdir, create_venv=False)

    manifest = json.loads((workdir / "manifest.json").read_text())
    assert manifest["schema_version"] == 1
    assert set(manifest["prompt_sha256"]) == {t.name for t in all_tasks()}
    for sha in manifest["prompt_sha256"].values():
        assert len(sha) == 64


def test_prepare_prompt_never_names_the_benchmark_or_its_traps(tmp_path):
    """Plan 15, trap 3: a leaked hint invalidates a run.

    This bans *meta* vocabulary — words that tell the agent it is being tested
    or that a hidden edge case exists. It deliberately does not ban domain
    terms like "antimeridian" or "nodata": in `split_antimeridian` the word is
    the function name, and in `geohash_neighbors` and `zonal_mean` it appears
    in the clause that pins the contract. Removing those would buy hint-freedom
    at the cost of spec ambiguity, which trap 4 rates as the worse defect.
    """
    workdir = tmp_path / "lab"
    prepare(workdir, create_venv=False)

    banned = ("geocase", "benchmark", "trap", "edge case", "gotcha", "be careful")
    for task in all_tasks():
        text = (workdir / "prompts" / f"{task.name}.md").read_text().lower()
        for word in banned:
            assert word not in text, f"{task.name} prompt leaks {word!r}"


def test_prepare_is_idempotent_and_keeps_generated_modules(tmp_path):
    workdir = tmp_path / "lab"
    prepare(workdir, create_venv=False)
    module = workdir / "generated" / "gen_length_m.py"
    module.write_text(GOOD_LENGTH_M)

    prepare(workdir, create_venv=False)
    assert module.read_text() == GOOD_LENGTH_M


def test_shuffled_order_is_seed_reproducible():
    a = shuffled_task_order(seed=7)
    b = shuffled_task_order(seed=7)
    c = shuffled_task_order(seed=8)
    assert a == b
    assert sorted(a) == sorted([t.name for t in all_tasks()])
    assert a != c  # vanishingly unlikely to collide across 20 tasks


# ---------------------------------------------------------------- ingest


def _fake_agent_session(workdir, task_name, source):
    """Stand-in for a coding-agent session: writes one module, nothing else."""
    (workdir / "generated" / get_task(task_name).module).write_text(
        textwrap.dedent(source)
    )


def test_ingest_grades_and_writes_a_run_record(tmp_path):
    workdir = tmp_path / "lab"
    prepare(workdir, create_venv=False)
    _fake_agent_session(workdir, "length_m", GOOD_LENGTH_M)
    _fake_agent_session(workdir, "wkt_from_latlon", TRAPPED_WKT)

    out = tmp_path / "runs"
    record = ingest(
        workdir,
        out_root=out,
        model_id="anthropic/claude-fable-5",
        label="Claude Code",
        protocol="claude-code",
        trial=1,
        date="2026-08-09",
    )

    assert record["schema_version"] == 2
    assert record["track"] == "agentic-manual"
    assert record["protocol"] == "claude-code"
    assert record["model"]["id"] == "anthropic/claude-fable-5"

    tasks = record["tasks"]
    assert tasks["length_m"]["trials"][0]["outcome"] == "CORRECT"
    assert tasks["wkt_from_latlon"]["trials"][0]["outcome"] == "SILENT"
    # Tasks the session never attempted are recorded, not omitted.
    assert tasks["buffer_m"]["trials"][0]["outcome"] == "MISSING"

    run_json = out / record["run_id"] / "run.json"
    assert json.loads(run_json.read_text())["run_id"] == record["run_id"]


def test_ingest_copies_modules_and_records_their_hashes(tmp_path):
    workdir = tmp_path / "lab"
    prepare(workdir, create_venv=False)
    _fake_agent_session(workdir, "length_m", GOOD_LENGTH_M)

    out = tmp_path / "runs"
    record = ingest(
        workdir,
        out_root=out,
        model_id="m/x",
        label="X",
        protocol="claude-code",
        trial=1,
        date="2026-08-09",
    )

    trial = record["tasks"]["length_m"]["trials"][0]
    copied = out / record["run_id"] / trial["module"]
    assert copied.is_file()
    assert copied.read_text() == (workdir / "generated" / "gen_length_m.py").read_text()
    assert len(trial["module_sha256"]) == 64


def test_ingest_carries_the_prompt_hashes_from_prepare(tmp_path):
    """Plan 15: a prompt edited between runs must be auditable after the fact."""
    workdir = tmp_path / "lab"
    prepare(workdir, create_venv=False)
    manifest = json.loads((workdir / "manifest.json").read_text())

    record = ingest(
        workdir,
        out_root=tmp_path / "runs",
        model_id="m/x",
        label="X",
        protocol="claude-code",
        trial=1,
        date="2026-08-09",
    )
    assert record["config"]["prompt_sha256"] == manifest["prompt_sha256"]


def test_ingest_extends_an_existing_run_with_a_second_trial(tmp_path):
    out = tmp_path / "runs"
    common = dict(
        out_root=out,
        model_id="m/x",
        label="X",
        protocol="claude-code",
        date="2026-08-09",
    )

    w1 = tmp_path / "lab1"
    prepare(w1, create_venv=False)
    _fake_agent_session(w1, "length_m", GOOD_LENGTH_M)
    ingest(w1, trial=1, **common)

    w2 = tmp_path / "lab2"
    prepare(w2, create_venv=False)
    _fake_agent_session(w2, "length_m", TRAPPED_WKT)  # wrong function: MISSING
    record = ingest(w2, trial=2, **common)

    trials = record["tasks"]["length_m"]["trials"]
    assert [t["trial"] for t in trials] == [1, 2]
    assert trials[0]["outcome"] == "CORRECT"
    assert trials[1]["outcome"] == "MISSING"
    assert record["config"]["trials"] == 2


def test_ingest_refuses_an_unprepared_directory(tmp_path):
    with pytest.raises(ManualRunError, match="manifest"):
        ingest(
            tmp_path / "nope",
            out_root=tmp_path / "runs",
            model_id="m/x",
            label="X",
            protocol="claude-code",
            trial=1,
            date="2026-08-09",
        )


def test_ingest_rejects_an_unknown_protocol(tmp_path):
    workdir = tmp_path / "lab"
    prepare(workdir, create_venv=False)
    with pytest.raises(ManualRunError, match="protocol"):
        ingest(
            workdir,
            out_root=tmp_path / "runs",
            model_id="m/x",
            label="X",
            protocol="telepathy",
            trial=1,
            date="2026-08-09",
        )
