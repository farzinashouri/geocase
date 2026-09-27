"""The `floor` CI job installs every core dependency at its declared minimum.

The pins live in `ci/floor-constraints.txt`; this test keeps them equal to the
`>=` bounds in `pyproject.toml`, so raising a floor without re-proving it
fails here instead of passing silently on a newer version.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSTRAINTS = ROOT / "ci" / "floor-constraints.txt"
_LOWER = re.compile(r"^([A-Za-z0-9_.-]+)\s*>=\s*([^,;\s]+)")


def _floors(requirements: list[str]) -> dict[str, str]:
    floors = {}
    for req in requirements:
        match = _LOWER.match(req)
        if match:
            floors[match.group(1).lower()] = match.group(2)
    return floors


def _pins() -> dict[str, str]:
    pins = {}
    for line in CONSTRAINTS.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, version = line.split("==")
            pins[name.strip().lower()] = version.strip()
    return pins


def test_every_core_dependency_is_pinned_at_its_floor() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    expected = _floors(project["dependencies"])
    expected["pytest"] = _floors(project["optional-dependencies"]["dev"])["pytest"]
    assert expected, "no >= bounds parsed from pyproject.toml"
    assert _pins() == expected
