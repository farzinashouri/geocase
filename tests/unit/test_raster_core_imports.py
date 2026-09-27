"""`geocase.raster` declares what it imports (issue #44).

The core install stays free of numpy (see test_packaging_extras.py), so every
third-party module `geocase.raster` imports at module level must come from the
core or from the `array` extra, and a missing numpy must say which extra to
install. Lazy imports inside functions (rasterio in `_writer.py`) belong to the
`write` extra and are not checked here.
"""

from __future__ import annotations

import ast
import importlib
import re
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RASTER = ROOT / "src" / "geocase" / "raster"
_NAME = re.compile(r"^[A-Za-z0-9_.-]+")


def _module_level_imports(path: Path) -> set[str]:
    names = set()
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def _names(requirements: list[str]) -> set[str]:
    return {m.group(0).lower() for r in requirements if (m := _NAME.match(r))}


def test_raster_module_level_imports_are_core_or_array_extra() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    allowed = _names(project["dependencies"]) | _names(
        project["optional-dependencies"]["array"]
    )
    imported: set[str] = set()
    for path in RASTER.rglob("*.py"):
        imported |= _module_level_imports(path)
    third_party = {
        name
        for name in imported
        if name not in sys.stdlib_module_names and name not in {"geocase", "__future__"}
    }
    assert "numpy" in third_party, "no numpy import found; the scan is broken"
    assert third_party <= allowed


def test_missing_numpy_names_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [m for m in sys.modules if m.startswith("geocase.raster")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "numpy", None)
    with pytest.raises(ImportError, match=re.escape("geocase[array]")):
        importlib.import_module("geocase.raster")
