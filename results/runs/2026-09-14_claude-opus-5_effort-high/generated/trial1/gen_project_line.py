"""Project WGS84 lines into a projected CRS while preserving their geodesic course.

A straight segment between two vertices in a projected CRS is almost never the
image of the shortest path on the ellipsoid: the further apart the vertices are
(and the further they sit from the projection's line of true scale), the more
the straight chord departs from the true course.  :func:`project_line` densifies
each input segment along its geodesic until the returned polyline stays within
``MAX_DEVIATION_M`` of that geodesic everywhere, measured in the target CRS.

The module has no import-time side effects; CRS/transformer construction is
deferred to the first call and cached.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Callable, List, Tuple

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["MAX_DEVIATION_M", "project_line"]

#: Contractual accuracy: the returned line never strays further than this
#: (in metres on the ground) from the geodesic it approximates.
MAX_DEVIATION_M = 25_000.0

# Each candidate piece is judged by sampling only three interior points, so aim
# at a fraction of the contractual tolerance to leave headroom for whatever the
# sampling misses between those points.
_TARGET_FRACTION = 0.5

# Never refine a whole input segment as a single piece: pre-split it into
# chunks of at most this arc length.  A long, symmetric projected image (an
# S-shape, say) can put all three sample points close to the chord even though
# the curve bulges elsewhere; starting from short chunks removes that blind
# spot at negligible cost.
_MAX_CHUNK_M = 500_000.0

# Backstops so a pathological CRS cannot make the refinement run away.
_MAX_DEPTH = 18
_MIN_ARC_M = 1.0

# Input coordinates are EPSG:4326, so "geodesic" means "geodesic on WGS84".
_GEOD = Geod(ellps="WGS84")

_XY = Tuple[float, float]


@lru_cache(maxsize=None)
def _transformer(dst_epsg: int) -> Transformer:
    """Cached lon/lat -> target CRS transformer (x/y order on both sides)."""
    return Transformer.from_crs(
        CRS.from_epsg(4326), CRS.from_epsg(dst_epsg), always_xy=True
    )


@lru_cache(maxsize=None)
def _tolerance_in_crs_units(dst_epsg: int) -> float:
    """``MAX_DEVIATION_M`` expressed in the target CRS's own axis units."""
    crs = CRS.from_epsg(dst_epsg)
    if crs.is_geographic:
        raise ValueError(
            f"EPSG:{dst_epsg} is a geographic CRS; project_line needs a projected one"
        )
    metres_per_unit = 1.0
    for axis in crs.axis_info:
        factor = getattr(axis, "unit_conversion_factor", None)
        if factor:
            metres_per_unit = float(factor)
            break
    return MAX_DEVIATION_M / metres_per_unit


def _point_to_segment_distance(p: _XY, a: _XY, b: _XY) -> float:
    """Distance from ``p`` to the segment ``a``-``b``; ``inf`` if anything is unprojectable."""
    px, py = p
    ax, ay = a
    bx, by = b
    if not all(math.isfinite(v) for v in (px, py, ax, ay, bx, by)):
        return math.inf
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / denom
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _refine(
    t0: float,
    t1: float,
    project_at: Callable[[float], _XY],
    arc: float,
    tol: float,
    depth: int,
) -> List[_XY]:
    """Return the projected vertices covering ``(t0, t1]``, subdividing as needed.

    ``t`` parametrises distance along the geodesic.  The piece is accepted once
    three interior samples of the true geodesic all lie within ``tol`` of the
    straight chord that would represent it in the output.
    """
    if depth >= _MAX_DEPTH or arc * (t1 - t0) <= _MIN_ARC_M:
        return [project_at(t1)]

    span = t1 - t0
    p0, p1 = project_at(t0), project_at(t1)
    error = max(
        _point_to_segment_distance(project_at(t0 + span * f), p0, p1)
        for f in (0.25, 0.5, 0.75)
    )
    if error <= tol:
        return [p1]

    mid = t0 + span * 0.5
    return _refine(t0, mid, project_at, arc, tol, depth + 1) + _refine(
        mid, t1, project_at, arc, tol, depth + 1
    )


def _densify_segment(
    start: Tuple[float, float],
    end: Tuple[float, float],
    transform: Callable[[float, float], _XY],
    tol: float,
) -> List[_XY]:
    """Projected vertices tracing the geodesic from ``start`` to ``end``, ends included."""
    lon1, lat1 = start
    lon2, lat2 = end
    azimuth, _, arc = _GEOD.inv(lon1, lat1, lon2, lat2)

    def at(t: float) -> Tuple[float, float]:
        if t <= 0.0:
            return lon1, lat1
        if t >= 1.0:
            return lon2, lat2
        lon, lat, _ = _GEOD.fwd(lon1, lat1, azimuth, arc * t)
        return lon, lat

    cache: dict = {}

    def project_at(t: float) -> _XY:
        xy = cache.get(t)
        if xy is None:
            xy = transform(*at(t))
            cache[t] = xy
        return xy

    chunks = 1 if not arc > 0.0 else max(1, math.ceil(arc / _MAX_CHUNK_M))
    points = [project_at(0.0)]
    for k in range(chunks):
        points.extend(
            _refine(k / chunks, (k + 1) / chunks, project_at, arc, tol, 0)
        )
    return points


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Reproject a WGS84 line into ``dst_epsg``, following the geodesic course.

    Parameters
    ----------
    line:
        A shapely ``LineString`` whose coordinates are longitude/latitude in
        EPSG:4326.  Any z values are dropped.
    dst_epsg:
        EPSG code of a projected CRS.

    Returns
    -------
    LineString
        The line in ``dst_epsg``.  Every input vertex is preserved, and extra
        vertices are inserted so that the polyline stays within
        ``MAX_DEVIATION_M`` (25 km) of the true geodesic between consecutive
        input vertices, everywhere along the line.

    Raises
    ------
    ValueError
        If the line has fewer than two vertices, if ``dst_epsg`` is not a
        projected CRS, or if part of the line falls outside the CRS's domain of
        validity (where coordinates are not finite).
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected a shapely LineString, got {type(line).__name__}")

    coords = [(float(c[0]), float(c[1])) for c in line.coords]
    if len(coords) < 2:
        raise ValueError("project_line needs a LineString with at least two vertices")

    dst_epsg = int(dst_epsg)
    tol = _tolerance_in_crs_units(dst_epsg) * _TARGET_FRACTION
    transform = _transformer(dst_epsg).transform

    points: List[_XY] = []
    for start, end in zip(coords, coords[1:]):
        piece = _densify_segment(start, end, transform, tol)
        # The first vertex of each piece repeats the previous piece's last one.
        points.extend(piece if not points else piece[1:])

    if any(not (math.isfinite(x) and math.isfinite(y)) for x, y in points):
        raise ValueError(
            f"the line cannot be represented in EPSG:{dst_epsg}: it reaches "
            "coordinates outside the projection's domain"
        )
    return LineString(points)