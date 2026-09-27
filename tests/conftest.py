"""Suite-wide hooks.

`@pytest.mark.requires("geopandas", ...)` skips a test whose optional modules
are not installed. The `floor` CI job runs the suite with no extras at the
lowest declared core versions; every test that needs an extra says so here
rather than failing there.
"""

from __future__ import annotations

import importlib.util

import pytest


def pytest_runtest_setup(item: pytest.Item) -> None:
    for marker in item.iter_markers(name="requires"):
        missing = [m for m in marker.args if importlib.util.find_spec(m) is None]
        if missing:
            pytest.skip(f"requires {', '.join(missing)}")
