"""Tests for the plugin's catalog helper, ``scripts/catalog.py`` (Plan 55 Phase 1).

The helper is run as a subprocess, the way the skills run it, against the real
bundled catalog. It is a consumer of the v1.0 surface, so the last tests pin
that it touches nothing outside ``geocase.__all__``.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import geocase

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "catalog.py"


def run(
    *args: str, python_flags: tuple[str, ...] = ()
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *python_flags, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def run_json(*args: str) -> Any:
    result = run(*args)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_cases_lists_the_whole_catalog() -> None:
    cases = run_json("cases")

    assert isinstance(cases, list)
    assert len(cases) == len(geocase.list_cases())
    for item in cases:
        assert {"id", "category", "risk_types", "title"} <= item.keys()


def test_cases_filters_match_list_cases() -> None:
    cases = run_json("cases", "--category", "vector", "--risk", "crs/axis_order")

    expected = geocase.list_cases(category="vector", risk_types_any=["crs/axis_order"])
    assert [item["id"] for item in cases] == [meta.id for meta in expected]
    assert cases, "the filter should select at least one bundled case"


def test_cases_risk_family_prefix_expands_like_list_cases() -> None:
    cases = run_json("cases", "--risk", "crs")

    expected = geocase.list_cases(risk_types_any=["crs"])
    assert [item["id"] for item in cases] == [meta.id for meta in expected]


def test_case_returns_metadata_and_notes_text() -> None:
    with_notes = next(
        meta for meta in geocase.list_cases() if geocase.load_case(meta.id).notes_path
    )
    notes_path = geocase.load_case(with_notes.id).notes_path
    assert notes_path is not None

    case = run_json("case", with_notes.id)

    assert isinstance(case, dict)
    assert case["id"] == with_notes.id
    assert case["risk_types"] == with_notes.risk_types
    assert "known_divergences" in case
    assert case["notes"] == notes_path.read_text(encoding="utf-8")


def test_case_unknown_id_exits_2() -> None:
    result = run("case", "no_such_case_id")

    assert result.returncode == 2
    assert "unknown case id" in result.stderr
    assert result.stdout == ""


def test_risks_returns_the_reverse_index_terms() -> None:
    risks = run_json("risks")

    assert isinstance(risks, dict)
    assert risks == geocase.risk_types()


def test_missing_geocase_exits_3_with_install_line(tmp_path: Path) -> None:
    # -S skips site-packages, so the installed geocase is not importable;
    # running from tmp_path keeps the repo's src/ off sys.path too.
    result = subprocess.run(
        [sys.executable, "-S", str(SCRIPT), "risks"],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )

    assert result.returncode == 3
    assert "pip install geocase" in result.stderr


def test_imports_only_the_public_surface() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    public = set(geocase.__all__)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("geocase."), alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("geocase."), node.module
            if node.module == "geocase":
                for alias in node.names:
                    assert alias.name in public, alias.name
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "geocase"
        ):
            assert node.attr in public, f"geocase.{node.attr}"
