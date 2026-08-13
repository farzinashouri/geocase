"""The oracle's own regression net (Plan 15 Phase 3, trap 1).

A wrong oracle silently mislabels every model — the failure mode this project
exists to name, turned on itself. For each new task this grades a known-good
implementation (must come back all-PASS) and a known-trapped one (must come
back SILENT on the edge check specifically, while passing the controls). The
ten Step 0 tasks carry the same guarantee through the committed-run pin test.
"""

import textwrap

import pytest

from geocase.benchmark._oracle_utils import (
    geohash_decode_bounds,
    geohash_encode,
    geohash_neighbors_oracle,
)
from geocase.benchmark.grading import grade_module
from geocase.benchmark.registry import get_task
from geocase.benchmark.taxonomy import CheckKind, Status

GOOD = {}
TRAPPED = {}


GOOD["tag_points"] = """
from shapely.geometry import Point

def tag_points(points, polygons):
    out = []
    for x, y in points:
        p = Point(x, y)
        idx = None
        for i, poly in enumerate(polygons):
            if poly.covers(p):
                idx = i
                break
        out.append(idx)
    return out
"""

TRAPPED["tag_points"] = """
from shapely.geometry import Point

def tag_points(points, polygons):
    out = []
    for x, y in points:
        p = Point(x, y)
        idx = None
        for i, poly in enumerate(polygons):
            if p.within(poly):  # boundary points silently fall through
                idx = i
                break
        out.append(idx)
    return out
"""

GOOD["fix_geometry"] = """
from shapely.validation import make_valid

def fix_geometry(geom):
    if geom.is_valid:
        return geom
    fixed = make_valid(geom)
    if fixed.geom_type == "GeometryCollection":
        from shapely.ops import unary_union
        polys = [g for g in fixed.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        fixed = unary_union(polys)
    return fixed
"""

TRAPPED["fix_geometry"] = """
def fix_geometry(geom):
    if geom.is_valid:
        return geom
    return geom.buffer(0)  # quietly deletes one bowtie lobe
"""

GOOD["dedupe_geoms"] = """
def dedupe_geoms(geoms):
    kept = []
    for g in geoms:
        if not any(g.equals(k) for k in kept):
            kept.append(g)
    return kept
"""

TRAPPED["dedupe_geoms"] = """
def dedupe_geoms(geoms):
    seen = set()
    kept = []
    for g in geoms:
        key = g.wkb  # misses rotated/reversed rings
        if key not in seen:
            seen.add(key)
            kept.append(g)
    return kept
"""

GOOD["to_rfc7946"] = """
import pyproj
from shapely.geometry import mapping
from shapely.geometry.polygon import orient
from shapely.ops import transform

def to_rfc7946(geom, epsg):
    if epsg != 4326:
        t = pyproj.Transformer.from_crs(epsg, 4326, always_xy=True).transform
        geom = transform(t, geom)
    if geom.geom_type == "Polygon":
        geom = orient(geom, 1.0)
    elif geom.geom_type == "MultiPolygon":
        from shapely.geometry import MultiPolygon
        geom = MultiPolygon([orient(p, 1.0) for p in geom.geoms])
    return dict(mapping(geom))
"""

TRAPPED["to_rfc7946"] = """
from shapely.geometry import mapping

def to_rfc7946(geom, epsg):
    return dict(mapping(geom))  # never reprojects: 3857 metres pass through
"""

GOOD["project_line"] = """
from pyproj import Geod, Transformer
from shapely.geometry import LineString

def project_line(line, dst_epsg):
    geod = Geod(ellps="WGS84")
    coords = list(line.coords)
    pts = [coords[0]]
    for (lo1, la1), (lo2, la2) in zip(coords, coords[1:]):
        pts.extend(geod.npts(lo1, la1, lo2, la2, 512))
        pts.append((lo2, la2))
    t = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    return LineString([t.transform(x, y) for x, y in pts])
"""

TRAPPED["project_line"] = """
from pyproj import Transformer
from shapely.geometry import LineString

def project_line(line, dst_epsg):
    # densifying after (or never) instead of before: vertices only
    t = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    return LineString([t.transform(x, y) for x, y in line.coords])
"""

GOOD["wkt_from_latlon"] = """
def wkt_from_latlon(lat, lon):
    return f"POINT ({lon} {lat})"
"""

TRAPPED["wkt_from_latlon"] = """
def wkt_from_latlon(lat, lon):
    return f"POINT ({lat} {lon})"  # swapped axes parse fine and look plausible
"""

GOOD["segment_intersection"] = """
from shapely.geometry import LineString

def segment_intersection(a, b):
    inter = LineString(a).intersection(LineString(b))
    if inter.is_empty:
        return None
    if inter.geom_type == "Point":
        return (inter.x, inter.y)
    coords = list(inter.coords)
    return (tuple(coords[0]), tuple(coords[-1]))
"""

TRAPPED["segment_intersection"] = """
def segment_intersection(a, b):
    (x1, y1), (x2, y2) = a
    (x3, y3), (x4, y4) = b
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if d == 0:
        return None  # collinear overlap silently reported as disjoint
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None
"""

_GEOHASH_TABLES = """
_BASE = "0123456789bcdefghjkmnpqrstuvwxyz"
_NEI = {
    "n": ["p0r21436x8zb9dcf5h7kjnmqesgutwvy", "bc01fg45238967deuvhjyznpkmstqrwx"],
    "s": ["14365h7k9dcfesgujnmqp0r2twvyx8zb", "238967debc01fg45kmstqrwxuvhjyznp"],
    "e": ["bc01fg45238967deuvhjyznpkmstqrwx", "p0r21436x8zb9dcf5h7kjnmqesgutwvy"],
    "w": ["238967debc01fg45kmstqrwxuvhjyznp", "14365h7k9dcfesgujnmqp0r2twvyx8zb"],
}
_BOR = {
    "n": ["prxz", "bcfguvyz"],
    "s": ["028b", "0145hjnp"],
    "e": ["bcfguvyz", "prxz"],
    "w": ["0145hjnp", "028b"],
}
"""

GOOD["geohash_neighbors"] = (
    _GEOHASH_TABLES
    + """
def _adjacent(gh, d):
    last, parent = gh[-1], gh[:-1]
    t = len(gh) % 2
    if last in _BOR[d][t] and parent:
        parent = _adjacent(parent, d)
    return parent + _BASE[_NEI[d][t].index(last)]

def geohash_neighbors(gh):
    n = _adjacent(gh, "n")
    s = _adjacent(gh, "s")
    return [n, s, _adjacent(gh, "e"), _adjacent(gh, "w"),
            _adjacent(n, "e"), _adjacent(n, "w"),
            _adjacent(s, "e"), _adjacent(s, "w")]
"""
)

TRAPPED["geohash_neighbors"] = (
    _GEOHASH_TABLES
    + """
def _adjacent(gh, d):
    last, parent = gh[-1], gh[:-1]
    t = len(gh) % 2
    # border handling omitted: cells across the equator or prime meridian
    # get a same-prefix neighbour that is simply the wrong cell
    return parent + _BASE[_NEI[d][t].index(last)]

def geohash_neighbors(gh):
    n = _adjacent(gh, "n")
    s = _adjacent(gh, "s")
    return [n, s, _adjacent(gh, "e"), _adjacent(gh, "w"),
            _adjacent(n, "e"), _adjacent(n, "w"),
            _adjacent(s, "e"), _adjacent(s, "w")]
"""
)

GOOD["split_antimeridian"] = """
from shapely.geometry import Polygon, box

def split_antimeridian(polygon):
    lons = [x for x, _ in polygon.exterior.coords]
    if not any(abs(a - b) > 180 for a, b in zip(lons, lons[1:])):
        return [polygon]
    shifted = Polygon([(x % 360, y) for x, y in polygon.exterior.coords])
    west = shifted.intersection(box(0, -90, 180, 90))
    east = shifted.intersection(box(180, -90, 360, 90))
    east = Polygon([(x - 360, y) for x, y in east.exterior.coords])
    return [west, east]
"""

TRAPPED["split_antimeridian"] = """
def split_antimeridian(polygon):
    return [polygon]  # a valid-looking list whose one part spans 358 degrees
"""

GOOD["zonal_mean"] = """
import rasterio
from shapely.geometry import Point

def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        arr = src.read(1)
        nodata = src.nodata
        vals = []
        for row in range(src.height):
            for col in range(src.width):
                x, y = src.transform * (col + 0.5, row + 0.5)
                if polygon.contains(Point(x, y)):
                    v = float(arr[row, col])
                    if nodata is None or v != nodata:
                        vals.append(v)
    return sum(vals) / len(vals) if vals else None
"""

TRAPPED["zonal_mean"] = """
import rasterio
import rasterio.mask
from shapely.geometry import mapping

def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        arr, _ = rasterio.mask.mask(src, [mapping(polygon)], crop=True)
    return float(arr[0].mean())  # nodata and fill pixels silently averaged in
"""

# ------------------------------------------------- stdlib domain (Plan 16 Phase 2)
# Same contract as the geo pairs: GOOD grades all-PASS, TRAPPED passes every
# control and returns a wrong value with no exception on the edge check.

GOOD["sample_variance"] = """
def sample_variance(values):
    vals = [float(v) for v in values]
    n = len(vals)
    if n < 2:
        return None
    mean = sum(vals) / n
    return sum((v - mean) ** 2 for v in vals) / (n - 1)
"""

TRAPPED["sample_variance"] = """
def sample_variance(values):
    vals = [float(v) for v in values]
    n = len(vals)
    if n < 2:
        return None
    # Textbook one-pass form: cancels to exactly 0.0 for large offsets.
    total = sum(vals)
    total_sq = sum(v * v for v in vals)
    return (total_sq - total * total / n) / (n - 1)
"""

GOOD["parse_delimited"] = """
import csv
import io

def parse_delimited(line):
    return next(csv.reader(io.StringIO(line)))
"""

TRAPPED["parse_delimited"] = """
def parse_delimited(line):
    return line.split(",")  # a comma inside quotes silently becomes a field break
"""

GOOD["dedupe_labels"] = """
import unicodedata

def dedupe_labels(labels):
    seen = set()
    out = []
    for label in labels:
        key = unicodedata.normalize("NFC", label).casefold()
        if key not in seen:
            seen.add(key)
            out.append(label)
    return out
"""

TRAPPED["dedupe_labels"] = """
def dedupe_labels(labels):
    seen = set()
    out = []
    for label in labels:
        key = label.casefold()  # folds case but not Unicode composition
        if key not in seen:
            seen.add(key)
            out.append(label)
    return out
"""

GOOD["group_means"] = """
def group_means(rows):
    totals = {}
    counts = {}
    for key, value in rows:
        totals.setdefault(key, 0.0)
        counts.setdefault(key, 0)
        if value is not None:
            totals[key] += float(value)
            counts[key] += 1
    return {k: (totals[k] / counts[k] if counts[k] else None) for k in totals}
"""

TRAPPED["group_means"] = """
def group_means(rows):
    totals = {}
    counts = {}
    for key, value in rows:
        totals[key] = totals.get(key, 0.0) + (value or 0.0)
        counts[key] = counts.get(key, 0) + (1 if value is not None else 0)
    # An all-None group divides nothing by nothing and reports a plain 0.0.
    return {k: (totals[k] / counts[k] if counts[k] else 0.0) for k in totals}
"""

GOOD["allocate_cents"] = """
def allocate_cents(total, weights):
    total_weight = sum(weights)
    shares = []
    allocated = 0
    for w in weights:
        share = int(total * w // total_weight)
        shares.append(share)
        allocated += share
    # Hand the rounding residue out one cent at a time, largest remainder first.
    remainders = sorted(
        range(len(weights)),
        key=lambda i: (total * weights[i] / total_weight) - shares[i],
        reverse=True,
    )
    for i in remainders[: total - allocated]:
        shares[i] += 1
    return shares
"""

TRAPPED["allocate_cents"] = """
def allocate_cents(total, weights):
    total_weight = sum(weights)
    # Each share rounded independently: the residue is silently dropped.
    return [int(round(total * w / total_weight)) for w in weights]
"""

GOOD["elapsed_hours"] = """
from datetime import datetime
from zoneinfo import ZoneInfo

def elapsed_hours(start, end, tz_name):
    tz = ZoneInfo(tz_name)
    a = datetime.fromisoformat(start).replace(tzinfo=tz)
    b = datetime.fromisoformat(end).replace(tzinfo=tz)
    delta = b.astimezone(ZoneInfo("UTC")) - a.astimezone(ZoneInfo("UTC"))
    return delta.total_seconds() / 3600.0
"""

TRAPPED["elapsed_hours"] = """
from datetime import datetime

def elapsed_hours(start, end, tz_name):
    # Naive subtraction: the zone is accepted and then ignored entirely.
    a = datetime.fromisoformat(start)
    b = datetime.fromisoformat(end)
    return (b - a).total_seconds() / 3600.0
"""


# ------------------------------------------- Plan 17 Phase 3 (corpus fixtures)

GOOD["geojson_bounds"] = """
import json

def geojson_bounds(path):
    with open(path) as fh:
        data = json.load(fh)
    geoms = [f["geometry"] for f in data["features"]]

    def coords(g):
        def walk(c):
            if c and isinstance(c[0], (int, float)):
                yield c
            else:
                for part in c:
                    yield from walk(part)
        return list(walk(g["coordinates"]))

    pts = [p for g in geoms for p in coords(g)]
    lats = [p[1] for p in pts]
    lons = sorted({p[0] for p in pts})
    # Choose the narrower of the two arcs the longitudes can span: if the gap
    # between two adjacent longitudes exceeds the wrap-around gap, the extent
    # crosses the antimeridian and the bbox runs max -> min.
    widest_gap = 0.0
    split = 0
    for i in range(len(lons)):
        gap = (lons[(i + 1) % len(lons)] - lons[i]) % 360.0
        if gap > widest_gap:
            widest_gap, split = gap, i
    min_lon = lons[(split + 1) % len(lons)]
    max_lon = lons[split]
    return (min_lon, min(lats), max_lon, max(lats))
"""

TRAPPED["geojson_bounds"] = """
import json

def geojson_bounds(path):
    with open(path) as fh:
        data = json.load(fh)

    def coords(g):
        def walk(c):
            if c and isinstance(c[0], (int, float)):
                yield c
            else:
                for part in c:
                    yield from walk(part)
        return list(walk(g["coordinates"]))

    pts = [p for f in data["features"] for p in coords(f["geometry"])]
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    # Plain min/max: for a polygon crossing the antimeridian this returns the
    # 358-degree complement — a whole-planet bbox, no exception, looks fine.
    return (min(lons), min(lats), max(lons), max(lats))
"""

GOOD["shapefile_attrs"] = """
from pathlib import Path

def shapefile_attrs(path):
    dbf = Path(path).with_suffix(".dbf")
    data = dbf.read_bytes()
    names = []
    offset = 32
    while offset < len(data) and data[offset] != 0x0D:
        names.append(data[offset:offset + 11].split(b"\\x00")[0].decode("ascii"))
        offset += 32
    return names
"""

TRAPPED["shapefile_attrs"] = """
from pathlib import Path

# Reads the names a caller expects rather than the ones the file stores. The
# .dbf truncated them to 10 characters when it was written, so this returns a
# plausible list of strings that the Shapefile does not actually contain.
_SCHEMA = {
    "truncated_fields": [
        "temperature_celsius",
        "temperature_fahrenheit",
        "precipitation_mm",
        "wind_speed_knots",
    ],
}

def shapefile_attrs(path):
    return list(_SCHEMA[Path(path).stem])
"""


# ------------------------------------------------ Plan 18 Phase 0 (product spec)

GOOD["s2_fixture"] = """
import numpy as np
import rasterio
from rasterio.transform import from_origin

def s2_fixture(path, size=32):
    data = np.arange(size * size, dtype="uint16").reshape(size, size) % 10000 + 1000
    with rasterio.open(
        path, "w", driver="GTiff", height=size, width=size, count=4,
        dtype="uint16", crs="EPSG:32633",
        transform=from_origin(500000, 6600000, 10, 10), nodata=0,
    ) as dst:
        for i, name in enumerate(["B2", "B3", "B4", "B8"], start=1):
            dst.write(data + i, i)
            dst.set_band_description(i, name)
        # Baseline 04.00: reflectance = (DN - 1000) / 10000. In GDAL's
        # value = raw*scale + offset convention the offset is in the scaled
        # unit, so -1000 DN is -0.1 reflectance.
        dst.scales = [1e-4] * 4
        dst.offsets = [-0.1] * 4
        dst.update_tags(PROCESSING_BASELINE="04.00",
                        QUANTIFICATION_VALUE="10000",
                        BOA_ADD_OFFSET="-1000")
"""

TRAPPED["s2_fixture"] = """
import numpy as np
import rasterio
from rasterio.transform import from_origin

def s2_fixture(path, size=32):
    # Plausible in every visible respect: right bands, right dtype, right grid.
    # The radiometry the baseline mandates is simply absent, so anything that
    # converts these DNs to reflectance is quietly off by 0.1 everywhere.
    data = np.arange(size * size, dtype="uint16").reshape(size, size) % 10000 + 1000
    with rasterio.open(
        path, "w", driver="GTiff", height=size, width=size, count=4,
        dtype="uint16", crs="EPSG:32633",
        transform=from_origin(500000, 6600000, 10, 10),
    ) as dst:
        for i, name in enumerate(["B2", "B3", "B4", "B8"], start=1):
            dst.write(data + i, i)
            dst.set_band_description(i, name)
"""


NEW_TASKS = sorted(GOOD)


def _grade(name, source, tmp_path):
    task = get_task(name)
    (tmp_path / task.module).write_text(textwrap.dedent(source))
    return task, grade_module(task, tmp_path)


@pytest.mark.parametrize("name", NEW_TASKS)
def test_known_good_passes_everything(name, tmp_path):
    _, outcome = _grade(name, GOOD[name], tmp_path)
    assert outcome.outcome == "CORRECT", [
        (c.check, c.status.value, c.detail) for c in outcome.checks
    ]


@pytest.mark.parametrize("name", NEW_TASKS)
def test_known_trapped_is_silent_on_the_edge_check(name, tmp_path):
    _, outcome = _grade(name, TRAPPED[name], tmp_path)
    by_kind = {}
    for c in outcome.checks:
        by_kind.setdefault(c.kind, []).append(c)
    assert all(c.status == Status.PASS for c in by_kind.get(CheckKind.CONTROL, [])), [
        (c.check, c.status.value, c.detail) for c in outcome.checks
    ]
    assert any(c.status == Status.SILENT for c in by_kind.get(CheckKind.EDGE, [])), [
        (c.check, c.status.value, c.detail) for c in outcome.checks
    ]
    assert outcome.outcome == "SILENT"


# ---------------------------------------------------------------- geohash oracle
# The oracle's geohash arithmetic itself, against published reference values.


def test_geohash_encode_reference_value():
    assert geohash_encode(-5.60302734375, 42.60498046875, 5) == "ezs42"


def test_geohash_decode_bounds_contains_center():
    w, s, e, n = geohash_decode_bounds("ezs42")
    assert w < -5.604 < e and s < 42.605 < n


def test_geohash_oracle_neighbors_of_interior_cell():
    # Reference neighbours of "ezs42" (geohash.org test vector).
    assert geohash_neighbors_oracle("ezs42") == {
        "ezs48",
        "ezs49",
        "ezs43",
        "ezs40",
        "ezs41",
        "ezefp",
        "ezefr",
        "ezefx",
    }
