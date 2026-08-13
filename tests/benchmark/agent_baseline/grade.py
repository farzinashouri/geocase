"""Step 0 grader — runs agent-generated implementations against inline oracles.

Plan 14, Step 0. Each generated module was produced by a fresh coding agent from
the neutral prompt committed under ``prompts/`` (no mention of edge cases, traps,
or GeoCase). This grader classifies every check as:

- PASS    — value within tolerance
- SILENT  — plausible-looking wrong value returned, nothing raised
- LOUD    — exception raised (an agent's own test run would catch this)
- MISSING — module or function absent

Oracles are constructed inline and expected values computed from pyproj.Geod /
first principles (Plan 14, trap 7: do not grade against unverified fixtures).

Usage: python grade.py [--generated DIR] [--json OUT.json]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import pyproj
from pyproj import Geod
from shapely.geometry import LineString, Point, Polygon, box

GEOD = Geod(ellps="WGS84")
HERE = Path(__file__).parent

RESULTS: list[dict] = []


def record(op, check, kind, status, detail=""):
    RESULTS.append(
        {
            "op": op,
            "check": check,
            "kind": kind,
            "status": status,
            "detail": str(detail),
        }
    )


def load(gen_dir: Path, name: str):
    path = gen_dir / f"gen_{name}.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"gen_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_check(op, check, kind, fn):
    """fn returns (ok: bool, detail: str); exceptions are LOUD."""
    try:
        ok, detail = fn()
    except Exception as exc:  # noqa: BLE001 — loud failure is a grading outcome
        record(op, check, kind, "LOUD", f"{type(exc).__name__}: {exc}")
        return
    record(op, check, kind, "PASS" if ok else "SILENT", detail)


def rel_ok(got, expected, tol):
    return abs(got - expected) <= tol * abs(expected)


# ---------------------------------------------------------------- area_m2
def grade_area_m2(mod):
    f = mod.area_m2

    def control():
        poly = box(13.0, 52.0, 13.1, 52.1)
        exp, _ = GEOD.geometry_area_perimeter(poly)
        exp = abs(exp)
        got = f(poly)
        return rel_ok(got, exp, 0.01), f"got {got:.4g}, expected {exp:.4g}"

    def dateline():
        # A 2-degree-wide, 1-degree-tall box crossing the antimeridian, as it
        # appears in real data: lons in [-180, 180]. Planar treatment computes
        # the 358-degree-wide complement instead.
        poly = Polygon([(179, 0), (-179, 0), (-179, 1), (179, 1)])
        ref = Polygon([(179, 0), (181, 0), (181, 1), (179, 1)])
        exp, _ = GEOD.geometry_area_perimeter(ref)
        exp = abs(exp)
        got = f(poly)
        return rel_ok(
            got, exp, 0.01
        ), f"got {got:.4g}, expected {exp:.4g} (2x1 deg box)"

    run_check("area_m2", "berlin_box", "control", control)
    run_check("area_m2", "antimeridian_box", "edge", dateline)


# ---------------------------------------------------------------- buffer_m
def grade_buffer_m(mod):
    f = mod.buffer_m

    def control():
        buf = f(Point(10, 50), 1000)
        lon_in, lat_in, _ = GEOD.fwd(10, 50, 90, 900)
        lon_out, lat_out, _ = GEOD.fwd(10, 50, 90, 1100)
        ok = (
            buf.is_valid
            and buf.intersects(Point(lon_in, lat_in))
            and not buf.intersects(Point(lon_out, lat_out))
        )
        return (
            ok,
            f"valid={buf.is_valid}, 900m in={buf.intersects(Point(lon_in, lat_in))}",
        )

    def dateline():
        buf = f(Point(179.9, 0), 50_000)
        # ~33.4 km east of the center, on the other side of the antimeridian.
        across = buf.intersects(Point(-179.8, 0)) or buf.intersects(Point(180.2, 0))
        # ~211 km west: must be outside.
        far = buf.intersects(Point(178.0, 0))
        w, _, e, _ = buf.bounds
        wrapped_world = (e - w) > 300  # bowtie smeared across the world
        ok = buf.is_valid and across and not far and not wrapped_world
        return ok, (
            f"valid={buf.is_valid}, across_dateline={across}, "
            f"contains_far_point={far}, lon_span={e - w:.1f}"
        )

    run_check("buffer_m", "1km_at_lat50", "control", control)
    run_check("buffer_m", "50km_across_dateline", "edge", dateline)


# ---------------------------------------------------------------- utm_epsg_for
def grade_utm_epsg_for(mod):
    f = mod.utm_epsg_for
    cases = [
        ("berlin", "control", (13.4, 52.5), 32633),
        ("buenos_aires_south", "control", (-58.4, -34.6), 32721),
        # Svalbard: zone 33X spans 9E-21E above 72N; the lon/6 formula says 32.
        ("svalbard_33X", "edge", (10.5, 78.0), 32633),
        # SW Norway: 32V is widened to 3E-12E between 56N and 64N; formula says 31.
        ("norway_32V", "edge", (4.5, 60.0), 32632),
    ]
    for name, kind, (lon, lat), exp in cases:

        def chk(lon=lon, lat=lat, exp=exp):
            got = f(lon, lat)
            return int(got) == exp, f"got {got}, expected {exp}"

        run_check("utm_epsg_for", name, kind, chk)


# ---------------------------------------------------------------- sample_at
def _make_raster(path: Path):
    import rasterio
    from rasterio.transform import from_origin

    transform = from_origin(500_000, 6_600_000, 100, 100)  # EPSG:32633, 100 m pixels
    data = np.full((10, 10), 42.0, dtype="float32")
    data[5, 5] = -9999.0
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
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)


def _pixel_lonlat(row, col):
    x = 500_000 + (col + 0.5) * 100
    y = 6_600_000 - (row + 0.5) * 100
    t = pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True)
    return t.transform(x, y)


def grade_sample_at(mod):
    f = mod.sample_at
    tmp = Path(tempfile.mkdtemp()) / "utm_nodata.tif"
    _make_raster(tmp)

    def control():
        lon, lat = _pixel_lonlat(2, 2)
        got = f(str(tmp), lon, lat)
        ok = (
            got is not None
            and not (isinstance(got, float) and math.isnan(got))
            and abs(float(got) - 42.0) < 1e-6
        )
        return ok, f"got {got!r}, expected 42.0"

    def nodata():
        lon, lat = _pixel_lonlat(5, 5)
        got = f(str(tmp), lon, lat)
        ok = got is None or (isinstance(got, float) and math.isnan(got))
        return ok, f"got {got!r}, expected None (pixel is the -9999 nodata sentinel)"

    run_check("sample_at", "valid_pixel_utm_raster", "control", control)
    run_check("sample_at", "nodata_sentinel", "edge", nodata)


# ---------------------------------------------------------------- label_point
def grade_label_point(mod):
    f = mod.label_point

    def control():
        poly = box(0, 0, 10, 10)
        p = f(poly)
        return p.within(poly), f"point {p.wkt}"

    def donut():
        poly = Polygon(
            [(0, 0), (10, 0), (10, 10), (0, 10)],
            holes=[[(2, 2), (8, 2), (8, 8), (2, 8)]],
        )
        p = f(poly)
        return p.within(poly), f"point {p.wkt} (centroid lies in the hole)"

    def c_shape():
        poly = Polygon(
            [(0, 0), (10, 0), (10, 10), (0, 10), (0, 8), (8, 8), (8, 2), (0, 2)]
        )
        p = f(poly)
        return p.within(poly), f"point {p.wkt} (centroid lies in the notch)"

    run_check("label_point", "square", "control", control)
    run_check("label_point", "donut", "edge", donut)
    run_check("label_point", "c_shape", "edge", c_shape)


# ---------------------------------------------------------------- tile_bounds
def _xyz_tile_bounds(z, x, y_xyz):
    n = 2**z

    def lon(xx):
        return xx / n * 360.0 - 180.0

    def lat(yy):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n))))

    return (lon(x), lat(y_xyz + 1), lon(x + 1), lat(y_xyz))


def grade_tile_bounds(mod):
    f = mod.tile_bounds

    def control():
        got = f(0, 0, 0)
        exp = _xyz_tile_bounds(0, 0, 0)
        ok = all(abs(g - e) < 1e-6 for g, e in zip(got, exp))
        return ok, f"got {got}"

    def tms_flip():
        # TMS row 1 at z=2 is XYZ row 2 (southern hemisphere band 0..-66.5).
        got = f(2, 1, 1)
        exp = _xyz_tile_bounds(2, 1, 2)
        ok = all(abs(g - e) < 1e-6 for g, e in zip(got, exp))
        return (
            ok,
            f"got {tuple(round(v, 4) for v in got)}, "
            f"expected {tuple(round(v, 4) for v in exp)}",
        )

    run_check("tile_bounds", "z0_world", "control", control)
    run_check("tile_bounds", "z2_tms_row_flip", "edge", tms_flip)


# ---------------------------------------------------------------- cluster_points_m
def _same(labels, i, j):
    return labels[i] == labels[j]


def grade_cluster_points_m(mod):
    f = mod.cluster_points_m

    def control():
        # ~300 m pair at the equator plus a point ~10 km away.
        labels = list(f([(0, 0), (0.0027, 0), (0.09, 0)], 500))
        ok = _same(labels, 0, 1) and not _same(labels, 0, 2)
        return ok, f"labels {labels}"

    def high_lat():
        # 0.012 deg of longitude at 75N is ~346 m — within 500 m.
        # A degrees-converted eps (500/111320) calls them separate.
        labels = list(f([(0, 75), (0.012, 75)], 500))
        return _same(labels, 0, 1), f"labels {labels} (points are ~346 m apart)"

    def dateline():
        labels = list(f([(179.999, 0), (-179.999, 0)], 500))
        return _same(labels, 0, 1), f"labels {labels} (points are ~222 m apart)"

    run_check("cluster_points_m", "300m_pair_plus_outlier", "control", control)
    run_check("cluster_points_m", "east_west_at_75N", "edge", high_lat)
    run_check("cluster_points_m", "pair_across_dateline", "edge", dateline)


# ---------------------------------------------------------------- length_m
def grade_length_m(mod):
    f = mod.length_m

    def control():
        line = LineString([(0, 0), (1, 0)])
        exp = GEOD.geometry_length(line)
        got = f(line)
        return rel_ok(got, exp, 0.005), f"got {got:.6g}, expected {exp:.6g}"

    def lat60():
        line = LineString([(0, 60), (1, 60)])
        exp = GEOD.geometry_length(line)  # ~55.8 km, not 111.32 km
        got = f(line)
        return rel_ok(got, exp, 0.005), f"got {got:.6g}, expected {exp:.6g}"

    def dateline():
        line = LineString([(179.5, 0), (-179.5, 0)])
        exp = GEOD.geometry_length(line)  # shortest path: ~111.3 km, not 359 deg
        got = f(line)
        return rel_ok(got, exp, 0.005), f"got {got:.6g}, expected {exp:.6g}"

    run_check("length_m", "1deg_equator", "control", control)
    run_check("length_m", "1deg_at_lat60", "edge", lat60)
    run_check("length_m", "1deg_across_dateline", "edge", dateline)


# ---------------------------------------------------------------- position_at
def grade_position_at(mod):
    f = mod.position_at

    def control():
        lon, lat = f([(0, 5.0, 50.0), (3600, 5.2, 50.2)], 900)
        ok = abs(lon - 5.05) < 0.01 and abs(lat - 50.05) < 0.01
        return ok, f"got ({lon:.4f}, {lat:.4f}), expected ~(5.05, 50.05)"

    def dateline():
        lon, lat = f([(0, 179.5, 10.0), (3600, -179.5, 10.2)], 1800)
        ok = abs(abs(lon) - 180.0) < 0.15 and 10.05 < lat < 10.15
        return (
            ok,
            f"got ({lon:.4f}, {lat:.4f}), "
            "expected lon near +/-180 (ship crosses the dateline)",
        )

    run_check("position_at", "quarter_along_leg", "control", control)
    run_check("position_at", "leg_across_dateline", "edge", dateline)


# ---------------------------------------------------------------- voronoi_cells
def grade_voronoi_cells(mod):
    f = mod.voronoi_cells
    pts = [(1, 1), (9, 2), (4, 7), (2, 9), (8, 8)]
    bounds = (0, 0, 10, 10)

    def partition():
        cells = f(pts, bounds)
        total = sum(c.area for c in cells)
        ok = len(cells) == len(pts) and rel_ok(total, 100.0, 0.01)
        return ok, f"{len(cells)} cells, total area {total:.3f}"

    def order():
        cells = f(pts, bounds)
        misses = [
            i for i, (c, p) in enumerate(zip(cells, pts)) if not c.contains(Point(p))
        ]
        return not misses, (
            f"cells not containing their own point: {misses or 'none'} "
            "(cell order must match input point order)"
        )

    run_check("voronoi_cells", "partition_of_bounds", "control", partition)
    run_check("voronoi_cells", "cell_order_matches_input", "edge", order)


# ---------------------------------------------------------------- main
GRADERS = {
    "area_m2": grade_area_m2,
    "buffer_m": grade_buffer_m,
    "utm_epsg_for": grade_utm_epsg_for,
    "sample_at": grade_sample_at,
    "label_point": grade_label_point,
    "tile_bounds": grade_tile_bounds,
    "cluster_points_m": grade_cluster_points_m,
    "length_m": grade_length_m,
    "position_at": grade_position_at,
    "voronoi_cells": grade_voronoi_cells,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated", type=Path, default=HERE / "generated")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    for name, grader in GRADERS.items():
        try:
            mod = load(args.generated, name)
        except Exception as exc:  # noqa: BLE001 — import-time crash is LOUD
            record(name, "import", "-", "LOUD", f"{type(exc).__name__}: {exc}")
            continue
        if mod is None or not hasattr(
            mod, name if name != "position_at" else "position_at"
        ):
            if mod is None or not hasattr(mod, name):
                record(
                    name, "import", "-", "MISSING", f"gen_{name}.py or function absent"
                )
                continue
        grader(mod)

    wid = max(len(r["op"]) for r in RESULTS) if RESULTS else 10
    print(f"{'operation':<{wid}}  {'check':<28} {'kind':<8} {'status':<8} detail")
    for r in RESULTS:
        print(
            f"{r['op']:<{wid}}  {r['check']:<28} {r['kind']:<8} "
            f"{r['status']:<8} {r['detail']}"
        )

    ops = {}
    for r in RESULTS:
        ops.setdefault(r["op"], []).append(r)
    silent = sum(
        1 for op, rs in ops.items() if any(x["status"] == "SILENT" for x in rs)
    )
    loud = sum(
        1
        for op, rs in ops.items()
        if any(x["status"] == "LOUD" for x in rs)
        and not any(x["status"] == "SILENT" for x in rs)
    )
    clean = sum(1 for op, rs in ops.items() if all(x["status"] == "PASS" for x in rs))
    print(
        f"\nper-operation: {clean} fully correct, {silent} with SILENT failures, "
        f"{loud} with only LOUD failures, of {len(ops)} graded"
    )

    if args.json:
        args.json.write_text(json.dumps(RESULTS, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
