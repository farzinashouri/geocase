"""Tests for the plugin's sandbox builder, ``scripts/sandbox.py`` (Plan 56 Phase 2)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT = SCRIPTS / "sandbox.py"
REPO = Path(__file__).resolve().parents[3]


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("geocase_plugin_sandbox", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    full = {**os.environ, **env}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=full,
        check=False,
    )


def test_sandbox_dir_uses_plugin_data(tmp_path: Path) -> None:
    got = _load().sandbox_dir({"CLAUDE_PLUGIN_DATA": str(tmp_path)}, home=Path("/h"))
    assert got == tmp_path / "sandbox"


def test_sandbox_dir_falls_back_to_cache() -> None:
    got = _load().sandbox_dir({}, home=Path("/h"))
    assert got == Path("/h/.cache/geocase-claude-plugin/sandbox")


def test_status_does_not_create(tmp_path: Path) -> None:
    proc = _run("status", env={"CLAUDE_PLUGIN_DATA": str(tmp_path)})
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["exists"] is False
    assert out["geocase_version"] is None
    assert not (tmp_path / "sandbox").exists()


def test_create_is_idempotent_and_runs_catalog(tmp_path: Path) -> None:
    env = {"CLAUDE_PLUGIN_DATA": str(tmp_path), "GEOCASE_SANDBOX_SPEC": str(REPO)}
    first = _run("create", env=env)
    assert first.returncode == 0, first.stderr
    info = json.loads(first.stdout)
    assert info["exists"] is True
    assert info["geocase_version"]
    marker = Path(info["python"]).parent.parent / "pyvenv.cfg"
    before = marker.stat().st_mtime_ns

    second = _run("create", env=env)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["geocase_version"] == info["geocase_version"]
    assert marker.stat().st_mtime_ns == before

    upgraded = _run("create", "--upgrade", env=env)
    assert upgraded.returncode == 0, upgraded.stderr

    risks = subprocess.run(
        [info["python"], str(SCRIPTS / "catalog.py"), "risks"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert risks.returncode == 0, risks.stderr
