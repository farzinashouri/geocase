```python
"""Project WGS84 line geometries into a projected CRS along true geodesics.

A straight segment between two WGS84 vertices does not, in general, stay
straight once projected: the shortest path on the ellipsoid (the geodesic)
maps to a curve in the target CRS.  :func:`project_line` densifies each input
segment along that geodesic until the projected polyline follows it to within
25 km everywhere.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import List, Sequence, Tuple

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

#: Maximum allowed deviation, in metres, between the returned polyline and the
#: true projected geodesic.
MAX_DEVIATION_M = 25_000.0

# Deviation is sampled at segment midpoints, so aim well inside the budget.
_TARGET_FRACTION = 0.4

# Every input segment is first cut into pieces of at most this geodesic length.
# This guards against symmetric cases where the midpoint of a long segment
# happens to land on the chord even though the geodesic bulges away from it.
_INITIAL_STEP_M = 100_000.0

# Each initial piece may be halved at most this many times (~24 m resolution).
_MAX_DEPTH = 12

_GEOD = Geod(ellps="WGS84")

_Point = Tuple[float, float]


@lru_cache(maxsize=32)
def _transformer(dst_epsg: int) -> Transformer:
    return Transformer.from_crs(
        CRS.from_epsg(4326), CRS.from_epsg(dst_epsg), always_xy=True
    )


@lru_cache(maxsize=32)
def _tolerance(dst_epsg: int) -> float:
    """Deviation budget expressed in the target CRS's own linear units."""
    crs = CRS.from_epsg(dst_epsg)
    metres_per_unit = 1.0
    try:
        factor = crs.axis_info[0].unit_conversion_factor
    except (AttributeError, IndexError):
        factor = None
    if factor and math.isfinite(factor) and factor > 0:
        metres_per_unit = factor
    return MAX_DEVIATION_M * _TARGET_FRACTION / metres_per_unit


def _finite(p: _Point) -> bool:
    return math.isfinite(p[0]) and math.isfinite(p[1])


def _point_to_segment_distance(p: _Point, a: _Point, b: _Point) -> float:
    """Planar distance from ``p`` to the segment ``a``-``b``."""
    px, py = p
    ax, ay = a
    bx, by = b
    dx = bx - ax
    dy = by - ay
    denom = dx * dx + dy * dy
    if denom == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / denom
    t = min(1.0, max(0.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _refine(
    transformer: Transformer,
    lon: float,
    lat: float,
    azimuth: float,
    s0: float,
    s1: float,
    p0: _Point,
    p1: _Point,
    tol: float,
    depth: int,
    out: List[_Point],
) -> None:
    """Append the projected geodesic strictly after ``s0`` through ``s1``.

    ``s0``/``s1`` are geodesic distances from ``(lon, lat)`` along ``azimuth``;
    ``p0``/``p1`` are their projected images.
    """
    if depth < _MAX_DEPTH and _finite(p0) and _finite(p1):
        sm = 0.5 * (s0 + s1)
        mid_lon, mid_lat, _ = _GEOD.fwd(lon, lat, azimuth, sm)
        pm = transformer.transform(mid_lon, mid_lat)
        # A non-finite midpoint means the projection is undefined there; no
        # amount of subdivision will help, so stop rather than emit garbage.
        if _finite(pm) and _point_to_segment_distance(pm, p0, p1) > tol:
            _refine(transformer, lon, lat, azimuth, s0, sm, p0, pm, tol, depth + 1, out)
            _refine(transformer, lon, lat, azimuth, sm, s1, pm, p1, tol, depth + 1, out)
            return
    out.append(p1)


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a WGS84 ``LineString`` into ``dst_epsg``, following geodesics.

    Parameters
    ----------
    line:
        A shapely ``LineString`` whose coordinates are longitude/latitude
        degrees in EPSG:4326.  Any Z values are dropped.
    dst_epsg:
        EPSG code of the target projected CRS.

    Returns
    -------
    LineString
        The line in ``dst_epsg``, densified so that it never strays more than
        25 km from the true projected geodesic between consecutive input
        vertices.  Input vertices are always retained.
    """
    if line.is_empty:
        return LineString()

    coords: Sequence[Sequence[float]] = list(line.coords)
    if len(coords) < 2:
        raise ValueError("project_line requires a LineString with at least 2 vertices")

    dst_epsg = int(dst_epsg)
    transformer = _transformer(dst_epsg)
    tol = _tolerance(dst_epsg)

    lon0, lat0 = float(coords[0][0]), float(coords[0][1])
    out: List[_Point] = [transformer.transform(lon0, lat0)]

    for start, end in zip(coords, coords[1:]):
        lon1, lat1 = float(start[0]), float(start[1])
        lon2, lat2 = float(end[0]), float(end[1])
        p_end = transformer.transform(lon2, lat2)

        azimuth, _, total = _GEOD.inv(lon1, lat1, lon2, lat2)
        if not math.isfinite(total) or total <= 0.0:
            out.append(p_end)
            continue

        pieces = max(1, math.ceil(total / _INITIAL_STEP_M))
        p_prev = out[-1]
        for i in range(pieces):
            s0 = total * i / pieces
            s1 = total * (i + 1) / pieces
            if i == pieces - 1:
                p_next = p_end
            else:
                nxt_lon, nxt_lat, _ = _GEOD.fwd(lon1, lat1, azimuth, s1)
                p_next = transformer.transform(nxt_lon, nxt_lat)
            _refine(
                transformer, lon1, lat1, azimuth, s0, s1, p_prev, p_next, tol, 0, out
            )
            p_prev = p_next

    return LineString(out)
```