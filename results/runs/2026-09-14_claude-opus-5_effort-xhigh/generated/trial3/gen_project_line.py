"""Project WGS84 lon/lat lines into a projected CRS along true geodesics.

A straight segment between two lon/lat vertices is not the shortest path on the
ellipsoid, and even the true geodesic is a curve once drawn in a projected CRS.
:func:`project_line` therefore densifies every input segment along its geodesic
until the returned polyline follows the projected geodesic to within
:data:`MAX_DEVIATION_M` everywhere.

Densification is adaptive and the deviation is measured *in the target CRS*, so
strongly distorting projections get the extra vertices they need while
well-behaved, short segments stay cheap.
"""

from __future__ import annotations

from functools import lru_cache
from math import hypot, isfinite
from typing import NamedTuple

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line", "MAX_DEVIATION_M"]

#: Maximum distance, in metres, between the returned polyline and the true
#: projected geodesic of the input.
MAX_DEVIATION_M = 25_000.0

_SOURCE_EPSG = 4326

# The deviation of a candidate segment is only sampled at a few points, so the
# refinement aims at a fraction of the budget and keeps headroom for whatever
# the curve does between the samples.
_SAFETY_FACTOR = 0.4

# Fractions along a candidate segment at which the deviation is sampled. More
# than just the midpoint, so an S-shaped segment whose midpoint happens to land
# on the chord is not mistaken for a straight one.
_PROBE_FRACTIONS = (0.25, 0.5, 0.75)
_MIDPOINT_INDEX = _PROBE_FRACTIONS.index(0.5)

# Fallback spacing for stretches that land outside the target CRS's domain of
# validity, where the projected deviation cannot be measured at all.
_UNPROJECTABLE_SPACING_M = 25_000.0

# Termination guards. They only bite where the deviation test cannot converge --
# a geodesic crossing the seam or the singularity of the target CRS is genuinely
# torn there, and no amount of splitting will close the gap.
_MIN_SEGMENT_M = 1.0
_MAX_DEPTH = 20
_MAX_ADDED_VERTICES = 200_000


class _Vertex(NamedTuple):
    """A point held in both CRSs at once, plus the z it carries through."""

    lon: float
    lat: float
    z: float
    x: float
    y: float


class _Context:
    """Everything the refinement needs, threaded through the recursion."""

    __slots__ = ("transformer", "geod", "tolerance", "budget")

    def __init__(self, transformer: Transformer, geod: Geod, tolerance: float):
        self.transformer = transformer
        self.geod = geod
        self.tolerance = tolerance
        self.budget = _MAX_ADDED_VERTICES


@lru_cache(maxsize=32)
def _setup(dst_epsg: int):
    """Transformer, ellipsoid and unit-corrected tolerance for *dst_epsg*."""
    source = CRS.from_epsg(_SOURCE_EPSG)
    target = CRS.from_epsg(dst_epsg)
    if not target.is_projected:
        raise ValueError(f"EPSG:{dst_epsg} is not a projected CRS")

    # State-plane style CRSs measure in feet; the tolerance is in metres.
    metres_per_unit = target.axis_info[0].unit_conversion_factor or 1.0
    geod = source.get_geod() or Geod(ellps="WGS84")
    transformer = Transformer.from_crs(source, target, always_xy=True)
    return transformer, geod, MAX_DEVIATION_M * _SAFETY_FACTOR / metres_per_unit


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Reproject *line* from EPSG:4326 into EPSG:*dst_epsg* along geodesics.

    Parameters
    ----------
    line:
        A :class:`shapely.geometry.LineString` whose coordinates are longitude
        and latitude in degrees on WGS84 (EPSG:4326). A z ordinate, if present,
        is interpolated linearly along each segment and carried through
        untransformed.
    dst_epsg:
        EPSG code of a projected CRS.

    Returns
    -------
    shapely.geometry.LineString
        The line in the target CRS, densified so that it stays within
        :data:`MAX_DEVIATION_M` of the projected geodesic joining each pair of
        consecutive input vertices. Vertices that fall outside the target CRS's
        domain of validity, and so project to infinity, are dropped.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected a LineString, got {type(line).__name__}")
    if line.is_empty:
        return LineString()

    transformer, geod, tolerance = _setup(int(dst_epsg))
    context = _Context(transformer, geod, tolerance)

    source_coords = list(line.coords)
    vertices = [_to_vertex(context, source_coords[0])]
    for raw in source_coords[1:]:
        current = _to_vertex(context, raw)
        vertices.extend(_refine(context, vertices[-1], current, 0))
        vertices.append(current)

    keep_z = line.has_z
    coords = [
        (vertex.x, vertex.y, vertex.z) if keep_z else (vertex.x, vertex.y)
        for vertex in vertices
        if isfinite(vertex.x) and isfinite(vertex.y)
    ]
    if len(coords) < 2:
        raise ValueError(
            f"line does not project into EPSG:{dst_epsg}: fewer than two "
            "vertices fall inside its domain of validity"
        )
    return LineString(coords)


def _to_vertex(context: _Context, coord) -> _Vertex:
    lon, lat = float(coord[0]), float(coord[1])
    z = float(coord[2]) if len(coord) > 2 else 0.0
    x, y = context.transformer.transform(lon, lat)
    return _Vertex(lon, lat, z, x, y)


def _refine(context: _Context, start: _Vertex, end: _Vertex, depth: int) -> list:
    """Vertices to insert strictly between *start* and *end*, in order."""
    azimuth, _, length = context.geod.inv(start.lon, start.lat, end.lon, end.lat)
    if not isfinite(length) or length <= _MIN_SEGMENT_M:
        return []
    if depth >= _MAX_DEPTH or context.budget <= 0:
        return []

    probes = _probe(context, start, azimuth, length, start.z, end.z)
    if _is_close_enough(context.tolerance, start, end, probes, length):
        return []

    middle = probes[_MIDPOINT_INDEX]
    context.budget -= 1
    return [
        *_refine(context, start, middle, depth + 1),
        middle,
        *_refine(context, middle, end, depth + 1),
    ]


def _probe(
    context: _Context,
    start: _Vertex,
    azimuth: float,
    length: float,
    z_start: float,
    z_end: float,
) -> list:
    """Sample the geodesic leaving *start* at the probe fractions of *length*."""
    count = len(_PROBE_FRACTIONS)
    lons, lats, _ = context.geod.fwd(
        [start.lon] * count,
        [start.lat] * count,
        [azimuth] * count,
        [fraction * length for fraction in _PROBE_FRACTIONS],
    )
    xs, ys = context.transformer.transform(lons, lats)
    return [
        _Vertex(lon, lat, z_start + fraction * (z_end - z_start), x, y)
        for fraction, lon, lat, x, y in zip(_PROBE_FRACTIONS, lons, lats, xs, ys)
    ]


def _is_close_enough(
    tolerance: float,
    start: _Vertex,
    end: _Vertex,
    probes: list,
    length: float,
) -> bool:
    """Does the chord *start*--*end* stand in for the geodesic well enough?"""
    if not all(isfinite(v.x) and isfinite(v.y) for v in (start, end, *probes)):
        # Part of this piece is outside the target CRS's domain, where the
        # projected deviation is undefined. Fall back to a fixed spacing on the
        # ground; the unprojectable vertices are dropped from the result.
        return length <= _UNPROJECTABLE_SPACING_M
    return all(
        _distance_to_segment(v.x, v.y, start.x, start.y, end.x, end.y) <= tolerance
        for v in probes
    )


def _distance_to_segment(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    """Distance from (px, py) to the segment (ax, ay)--(bx, by)."""
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    squared_length = vx * vx + vy * vy
    if squared_length > 0.0:
        t = (wx * vx + wy * vy) / squared_length
        t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
        wx -= t * vx
        wy -= t * vy
    return hypot(wx, wy)