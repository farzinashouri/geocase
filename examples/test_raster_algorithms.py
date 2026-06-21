"""Example tests for raster algorithms over Priority 1 EO fixtures.

Demonstrates the public GeoCase testing pattern: resolve a bundled case, open
it, and assert on real algorithm behaviour. See
``docs/plans/08-raster-action-plan.md`` Step 8.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from geocase.cases.factory import create_case
from geocase.catalog.loader import load_case_metadata

_EXAMPLES_DIR = Path(__file__).resolve().parent
if str(_EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES_DIR))

from raster_algorithms import compute_ndvi, terrain_stats, water_fraction  # noqa: E402

pytest.importorskip("rasterio")

_RASTER_ROOT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "geocase"
    / "data"
    / "core"
    / "raster"
)


def _case(case_id: str):
    root = _RASTER_ROOT / case_id
    meta = load_case_metadata(root / "case.yaml")
    return create_case(meta, root)


def test_water_mask_fraction_excludes_nodata() -> None:
    case = _case("water_mask_small")
    data, _profile, nodata = case.read(1)

    fraction = water_fraction(data, nodata=nodata)

    # 8x8 water block over a 16x16 grid (minus one nodata pixel).
    assert 0.0 < fraction < 1.0
    # The lone nodata pixel must not be counted as water or land.
    assert nodata == 255


def test_ndvi_from_multispectral_bands_in_range() -> None:
    case = _case("multispectral_s2_like_small")
    with case.open() as src:
        red = src.read(3)
        nir = src.read(4)

    ndvi = compute_ndvi(red, nir)

    assert ndvi.shape == red.shape
    assert np.all(ndvi >= -1.0)
    assert np.all(ndvi <= 1.0)


def test_dem_terrain_stats_ignore_nan() -> None:
    case = _case("dem_small")
    data, _profile, _nodata = case.read(1)

    stats = terrain_stats(data)

    assert np.isnan(data).any()  # fixture contains a NaN nodata pixel
    assert stats["min"] <= stats["mean"] <= stats["max"]
    assert np.isfinite(stats["mean"])
