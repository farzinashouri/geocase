"""`@pytest.mark.requires(...)` skips a test when an optional module is absent.

The `floor` CI job installs no extras, so every test that reads data through
geopandas / rasterio / xarray must say so. An explicit marker rather than a
hook that turns any ModuleNotFoundError into a skip: that hook would also
skip a core code path that wrongly imports an extra, which is exactly what
the floor job exists to catch.
"""

from __future__ import annotations

import pytest


@pytest.mark.requires("geocase_module_that_does_not_exist")
def test_is_skipped_when_the_module_is_missing() -> None:
    pytest.fail("the requires marker did not skip this test")


@pytest.mark.requires("json")
def test_runs_when_the_module_is_present() -> None:
    import json

    assert json.loads("1") == 1
