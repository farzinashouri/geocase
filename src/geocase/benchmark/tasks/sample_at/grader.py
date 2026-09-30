"""Oracle for sample_at, ported verbatim from the Step 0 grader."""

import math
import tempfile
from pathlib import Path

import numpy as np
import pyproj

from geocase.benchmark._oracle_utils import make_utm_nodata_raster, utm_pixel_lonlat


def _write(name, transform, data, nodata):
    import rasterio

    path = Path(tempfile.mkdtemp()) / f"{name}.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:32633",
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)
    return path


def _lonlat(transform, row, col):
    x, y = transform * (col + 0.5, row + 0.5)
    t = pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True)
    return t.transform(x, y)


def _is_missing(got):
    return got is None or (isinstance(got, float) and math.isnan(got))


def build_checks(f):
    tmp = Path(tempfile.mkdtemp()) / "utm_nodata.tif"
    make_utm_nodata_raster(tmp)

    def control():
        lon, lat = utm_pixel_lonlat(2, 2)
        got = f(str(tmp), lon, lat)
        ok = (
            got is not None
            and not (isinstance(got, float) and math.isnan(got))
            and abs(float(got) - 42.0) < 1e-6
        )
        return ok, f"got {got!r}, expected 42.0"

    def nodata():
        lon, lat = utm_pixel_lonlat(5, 5)
        got = f(str(tmp), lon, lat)
        ok = got is None or (isinstance(got, float) and math.isnan(got))
        return ok, f"got {got!r}, expected None (pixel is the -9999 nodata sentinel)"

    def _nodata_at(name, transform, note):
        data = np.full((10, 10), 42.0, dtype="float32")
        data[5, 5] = -9999.0
        path = _write(name, transform, data, -9999.0)
        lon, lat = _lonlat(transform, 5, 5)
        got = f(str(path), lon, lat)
        return _is_missing(got), f"got {got!r}, expected None ({note})"

    def bottom_up():
        from rasterio.transform import Affine

        t = Affine(100, 0, 500_000, 0, 100, 6_599_000)
        return _nodata_at("bottom_up", t, "bottom-up raster, sentinel pixel")

    def non_square():
        from rasterio.transform import from_origin

        t = from_origin(500_000, 6_600_000, 100, 250)
        return _nodata_at("non_square", t, "100 x 250 m pixels, sentinel pixel")

    def nan_nodata_keeps_real_value():
        from rasterio.transform import from_origin

        t = from_origin(500_000, 6_600_000, 100, 100)
        data = np.full((10, 10), 42.0, dtype="float32")
        data[5, 5] = float("nan")
        data[6, 6] = -9999.0  # valid data when nodata is NaN
        path = _write("nan_nodata", t, data, float("nan"))
        lon, lat = _lonlat(t, 6, 6)
        got = f(str(path), lon, lat)
        ok = got is not None and abs(float(got) + 9999.0) < 1e-6
        return ok, f"got {got!r}, expected -9999.0 (real value when nodata is NaN)"

    return [
        ("valid_pixel_utm_raster", "control", control),
        ("nodata_sentinel", "edge", nodata),
        ("bottom_up_sentinel", "edge", bottom_up),
        ("non_square_sentinel", "edge", non_square),
        ("nan_nodata_keeps_minus_9999", "edge", nan_nodata_keeps_real_value),
    ]
