"""Oracle for zonal_mean (RAS-0024): NoData sentinel plus partial edge pixels.
The oracle loops pixel centres explicitly and excludes the sentinel; masking
without the nodata filter averages -9999 values in."""

import tempfile
from pathlib import Path

import numpy as np
from shapely.geometry import Point, box

from geocase.benchmark._oracle_utils import rel_ok

# EPSG:32633, 100 m pixels, origin (500000, 6600000); value = row*10 + col,
# nodata -9999 at (2,2) and (2,3).
NODATA = -9999.0


def _make_raster(path: Path) -> None:
    import rasterio
    from rasterio.transform import from_origin

    data = np.array(
        [[r * 10 + c for c in range(10)] for r in range(10)], dtype="float32"
    )
    data[2, 2] = NODATA
    data[2, 3] = NODATA
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:32633",
        transform=from_origin(500_000, 6_600_000, 100, 100),
        nodata=NODATA,
    ) as dst:
        dst.write(data, 1)


def _expected_mean(poly) -> float:
    vals = []
    for r in range(10):
        for c in range(10):
            x = 500_000 + (c + 0.5) * 100
            y = 6_600_000 - (r + 0.5) * 100
            v = float(r * 10 + c) if (r, c) not in [(2, 2), (2, 3)] else NODATA
            if v != NODATA and poly.contains(Point(x, y)):
                vals.append(v)
    return sum(vals) / len(vals)


def build_checks(f):
    tmp = Path(tempfile.mkdtemp()) / "zonal.tif"
    _make_raster(tmp)

    def control():
        # Aligned exactly to rows 5-7, all columns; no nodata anywhere near.
        poly = box(500_000, 6_599_200, 501_000, 6_599_500)
        exp = _expected_mean(poly)
        got = f(str(tmp), poly)
        ok = got is not None and rel_ok(float(got), exp, 1e-6)
        return ok, f"got {got!r}, expected {exp}"

    def nodata_and_partial():
        # Cuts through pixels partway (centres of rows 1-3, cols 1-4 are in;
        # the box also grazes row 0 without containing its centres) and covers
        # the two nodata cells.
        poly = box(500_120, 6_599_620, 500_480, 6_599_920)
        exp = _expected_mean(poly)
        got = f(str(tmp), poly)
        ok = got is not None and rel_ok(float(got), exp, 1e-6)
        return ok, (
            f"got {got!r}, expected {exp} (pixel-centre rule, -9999 sentinel excluded)"
        )

    return [
        ("full_clean_region", "control", control),
        ("partial_pixels_and_nodata", "edge", nodata_and_partial),
    ]
