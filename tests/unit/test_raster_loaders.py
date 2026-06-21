"""Exercises raster loader helpers against bundled GeoTIFF fixtures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("rasterio")

from geocase.assertions.raster import (
    assert_band_count,
    assert_band_names,
    assert_dtype,
    assert_nan_nodata,
    assert_nodata_value,
)
from geocase.loaders import rasterio_loader

_RASTER_ROOT = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "geocase"
    / "data"
    / "core"
    / "raster"
)


def _primary(case_id: str, name: str | None = None) -> Path:
    name = name or f"{case_id}.tif"
    return _RASTER_ROOT / case_id / name


def test_open_raster_yields_dataset():
    with rasterio_loader.open_raster(_primary("optical_rgb_small")) as src:
        assert_band_count(src, 3)
        assert_dtype(src, "uint8")
        assert_band_names(src, ["red", "green", "blue"])


def test_open_raster_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        with rasterio_loader.open_raster(tmp_path / "nope.tif"):
            pass


def test_load_all_bands_returns_3d_array():
    data, profile, nodata = rasterio_loader.load(
        _primary("multispectral_s2_like_small")
    )
    assert data.shape == (4, 16, 16)
    assert profile["dtype"] == "uint16"
    assert nodata == 0


def test_load_single_band():
    data, _profile, _nodata = rasterio_loader.load(
        _primary("ndvi_small"), band=1
    )
    assert data.shape == (16, 16)
    assert float(data.min()) >= -1.0001
    assert float(data.max()) <= 1.0001


def test_water_mask_nodata_sentinel():
    with rasterio_loader.open_raster(_primary("water_mask_small")) as src:
        assert_nodata_value(src, 255)


def test_dem_nan_nodata():
    with rasterio_loader.open_raster(_primary("dem_small")) as src:
        assert_nan_nodata(src)
        data = src.read(1)
    assert np.isnan(data).any()
