"""Oracle for zonal_mean (RAS-0024): NoData sentinel plus partial edge pixels.
The oracle loops pixel centres explicitly and excludes the sentinel; masking
without the nodata filter averages -9999 values in."""

import math
import tempfile
from pathlib import Path

import numpy as np
from shapely.geometry import Point, box

from geocase.benchmark._oracle_utils import rel_ok

# EPSG:32633, 100 m pixels, origin (500000, 6600000); value = row*10 + col,
# nodata -9999 at (2,2) and (2,3).
NODATA = -9999.0

SOURCES = {
    "NODATA": "author-chosen: the sentinel written into the synthetic raster's "
    "own header, which is where the model's code must read it from",
}


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


def _write(path: Path, transform, data, nodata: float) -> None:
    import rasterio

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


def _grid(bad: dict) -> np.ndarray:
    """value = row*10 + col, with the given {(row, col): value} overrides."""
    data = np.array(
        [[r * 10 + c for c in range(10)] for r in range(10)], dtype="float32"
    )
    for (r, c), v in bad.items():
        data[r, c] = v
    return data


def _expected_from(data, transform, poly):
    """Pixel-centre rule; the -9999 sentinel and NaN are both excluded."""
    vals = []
    for r in range(10):
        for c in range(10):
            x, y = transform * (c + 0.5, r + 0.5)
            v = float(data[r, c])
            if v != NODATA and not math.isnan(v) and poly.contains(Point(x, y)):
                vals.append(v)
    return sum(vals) / len(vals) if vals else None


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

    def _battery(name, transform, data, poly, note):
        path = Path(tempfile.mkdtemp()) / f"{name}.tif"
        _write(path, transform, data, NODATA)
        exp = _expected_from(data, transform, poly)
        got = f(str(path), poly)
        if exp is None:
            ok = got is None or (isinstance(got, float) and math.isnan(got))
        else:
            ok = got is not None and rel_ok(float(got), exp, 1e-6)
        return ok, f"got {got!r}, expected {exp!r} ({note})"

    holes = {(2, 2): NODATA, (2, 3): NODATA}

    def bottom_up():
        # Positive y pixel size: row 0 is the southern edge.
        from rasterio.transform import Affine

        t = Affine(100, 0, 500_000, 0, 100, 6_599_000)
        poly = box(500_120, 6_599_120, 500_480, 6_599_320)
        return _battery("bottom_up", t, _grid(holes), poly, "bottom-up transform")

    def non_square():
        from rasterio.transform import from_origin

        t = from_origin(500_000, 6_600_000, 100, 200)
        poly = box(500_120, 6_599_350, 500_480, 6_599_950)
        return _battery("non_square", t, _grid(holes), poly, "100 x 200 m pixels")

    def all_nodata_window():
        from rasterio.transform import from_origin

        t = from_origin(500_000, 6_600_000, 100, 100)
        poly = box(500_200, 6_599_700, 500_400, 6_599_800)
        return _battery(
            "all_nodata", t, _grid(holes), poly, "only nodata centres: no value"
        )

    def nan_beside_sentinel():
        from rasterio.transform import from_origin

        t = from_origin(500_000, 6_600_000, 100, 100)
        data = _grid({(2, 2): NODATA, (2, 3): float("nan"), (3, 3): float("nan")})
        poly = box(500_120, 6_599_620, 500_480, 6_599_920)
        return _battery("nan_beside", t, data, poly, "NaN beside the -9999 sentinel")

    return [
        ("full_clean_region", "control", control),
        ("partial_pixels_and_nodata", "edge", nodata_and_partial),
        ("bottom_up_transform", "edge", bottom_up),
        ("non_square_pixels", "edge", non_square),
        ("all_nodata_window", "edge", all_nodata_window),
        ("nan_beside_sentinel", "edge", nan_beside_sentinel),
    ]
