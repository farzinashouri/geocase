"""Tests for the plugin's environment detector, ``scripts/env.py`` (Plan 56 Phase 1).

``detect`` is a pure function of env vars, files and prefixes, so each row of
the table is a fake environment built in ``tmp_path``.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "env.py"
PY = "/fake/bin/python"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("geocase_plugin_env", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def detect(
    tmp_path: Path,
    *,
    env: dict[str, str] | None = None,
    files: dict[str, str] | None = None,
    in_venv: bool = False,
    externally_managed: bool = False,
    version: str | None = "1.2.3",
) -> dict[str, Any]:
    project = tmp_path / "project"
    project.mkdir()
    for name, text in (files or {}).items():
        (project / name).write_text(text)
    stdlib = tmp_path / "stdlib"
    stdlib.mkdir()
    if externally_managed:
        (stdlib / "EXTERNALLY-MANAGED").write_text("[externally-managed]\n")
    return _load().detect(
        env=env or {},
        project=project,
        version=version,
        python=PY,
        prefix="/venv" if in_venv else "/usr",
        base_prefix="/usr",
        stdlib=stdlib,
    )


def test_pixi_env_var(tmp_path: Path) -> None:
    out = detect(tmp_path, env={"PIXI_PROJECT_MANIFEST": "/p/pixi.toml"})
    assert out["manager"] == "pixi"
    assert out["command"] == "pixi add --pypi geocase==1.2.3"
    assert out["edits_manifest"] is True
    assert out["installable"] is True


def test_pixi_toml(tmp_path: Path) -> None:
    assert detect(tmp_path, files={"pixi.toml": ""})["manager"] == "pixi"


def test_pixi_in_pyproject(tmp_path: Path) -> None:
    out = detect(tmp_path, files={"pyproject.toml": "[tool.pixi.project]\n"})
    assert out["manager"] == "pixi"


def test_uv(tmp_path: Path) -> None:
    out = detect(tmp_path, files={"uv.lock": ""})
    assert out["manager"] == "uv"
    assert out["command"] == "uv add --dev geocase==1.2.3"
    assert out["edits_manifest"] is True


def test_poetry(tmp_path: Path) -> None:
    out = detect(tmp_path, files={"poetry.lock": ""})
    assert out["manager"] == "poetry"
    assert out["command"] == "poetry add --group dev geocase==1.2.3"
    assert out["edits_manifest"] is True


def test_conda_named_env(tmp_path: Path) -> None:
    out = detect(
        tmp_path, env={"CONDA_PREFIX": "/c/envs/work", "CONDA_DEFAULT_ENV": "work"}
    )
    assert out["manager"] == "conda"
    assert out["command"] == f"{PY} -m pip install geocase==1.2.3"
    assert out["edits_manifest"] is False
    assert out["installable"] is True


def test_venv(tmp_path: Path) -> None:
    out = detect(tmp_path, in_venv=True)
    assert out["manager"] == "venv"
    assert out["command"] == f"{PY} -m pip install geocase==1.2.3"
    assert out["installable"] is True


def test_conda_base_is_refused(tmp_path: Path) -> None:
    out = detect(tmp_path, env={"CONDA_PREFIX": "/c", "CONDA_DEFAULT_ENV": "base"})
    assert out["installable"] is False
    assert out["command"] is None
    assert "base" in out["reason"]


def test_externally_managed_is_refused(tmp_path: Path) -> None:
    out = detect(tmp_path, externally_managed=True)
    assert out["installable"] is False
    assert out["command"] is None
    assert "EXTERNALLY-MANAGED" in out["reason"]


def test_venv_beats_externally_managed(tmp_path: Path) -> None:
    out = detect(tmp_path, in_venv=True, externally_managed=True)
    assert out["manager"] == "venv"
    assert out["installable"] is True


@pytest.mark.parametrize(
    ("env", "files", "expected"),
    [
        ({"CONDA_PREFIX": "/c", "CONDA_DEFAULT_ENV": "w"}, {"pixi.toml": ""}, "pixi"),
        (
            {"CONDA_PREFIX": "/c", "CONDA_DEFAULT_ENV": "w"},
            {"uv.lock": "", "poetry.lock": ""},
            "uv",
        ),
        ({}, {"pixi.toml": "", "uv.lock": ""}, "pixi"),
    ],
)
def test_priority_order(
    tmp_path: Path, env: dict[str, str], files: dict[str, str], expected: str
) -> None:
    assert detect(tmp_path, env=env, files=files)["manager"] == expected


def test_no_version_means_no_pin(tmp_path: Path) -> None:
    out = detect(tmp_path, files={"uv.lock": ""}, version=None)
    assert out["command"] == "uv add --dev geocase"


def test_cli_prints_json(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "detect",
            "--version",
            "9.9.9",
            "--project",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert set(out) == {
        "manager",
        "python",
        "installable",
        "command",
        "reason",
        "edits_manifest",
    }
    assert out["manager"] == "uv"
    assert out["command"] == "uv add --dev geocase==9.9.9"
