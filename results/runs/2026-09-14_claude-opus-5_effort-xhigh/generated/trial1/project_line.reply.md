```python
"""Reproject WGS84 line geometries so that the result follows the true geodesic.

A ``LineString`` is a sequence of *straight* segments in whatever coordinate
system it happens to live in.  Projecting the vertices of a WGS84 line one at a
time and joining them up in the target CRS therefore draws a path that is
generally **not** the shortest path on the ellipsoid -- a Sydney -> Santiago leg
drawn that way misses the real course by thousands of kilometres.

:func:`project_line` densifies every input segment along its geodesic before
projecting, adaptively and only where it is needed, until the straight-line
rendering in the target CRS stays within ``tolerance_m`` of the projected
geodesic everywhere.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import List, Optional, Tuple

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line", "DEFAULT_TOLERANCE_M"]

#: Required accuracy of the traced geodesic, in metres.
DEFAULT_TOLERANCE_M = 25_000.0

# Fractions along a sub-segment at which the geodesic is compared against the
# straight chord.  0.5 must stay in the tuple: that sample doubles as the split
# point when a sub-segment is rejected.
_SAMPLE_FRACTIONS: Tuple[float, ...] = (0.25, 0.5, 0.75)

# Midpoint sampling can only estimate the true maximum deviation, so accept a
# sub-segment at half the requested tolerance.  Convergence is quadratic, so
# this margin costs well under one extra level of subdivision.
_SAFETY = 0.5

# A branch that still looks bad once its endpoints are a millimetre apart on the
# ground is sitting on a discontinuity of the projection (an antimeridian seam,
# say), not on a poorly approximated curve.  More vertices cannot help there.
_MIN_SEGMENT_M = 1e-3
_MAX_DEPTH = 20

# A projected point in the target CRS, carrying its WGS84 source: (lon, lat, x, y).
_Node = Tuple[float, float, float, float]


@lru_cache(maxsize=None)
def _projection(dst_epsg: int) -> Tuple[Transformer, Geod, float]:
    """Return the transformer, ellipsoid and CRS-unit size for ``dst_epsg``.

    Cached because building a ``Transformer`` costs far more than using one.
    """
    src = CRS.from_epsg(4326)
    dst = CRS.from_epsg(dst_epsg)
    if not dst.is_projected:
        raise ValueError(
            f"EPSG:{dst_epsg} is not a projected CRS "
            f"({dst.name!r}); project_line needs a planar target"
        )
    transformer = Transformer.from_crs(src, dst, always_xy=True)
    # Target CRS axis units expressed in metres (1.0 for metre-based CRSs,
    # ~0.3048 for the foot-based state plane and similar codes).
    axes = dst.axis_info
    unit = axes[0].unit_conversion_factor if axes else 1.0
    geod = src.get_geod() or Geod(ellps="WGS84")
    return transformer, geod, unit


def _point_to_segment(px: float, py: float, ax: float, ay: float,
                      bx: float, by: float) -> float:
    """Shortest distance from ``p`` to the finite segment ``a``-``b``."""
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    vv = vx * vx + vy * vy
    if vv == 0.0:
        return math.hypot(wx, wy)
    t = (wx * vx + wy * vy) / vv
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def _deviation(start: _Node, end: _Node, geod: Geod, transformer: Transformer,
               dst_epsg: int) -> Optional[Tuple[float, _Node]]:
    """Measure how far the chord ``start``-``end`` strays from the geodesic.

    Returns ``(deviation_in_crs_units, geodesic_midpoint)``, or ``None`` when
    the two ends are so close together that subdividing cannot improve matters.
    """
    lon1, lat1, x1, y1 = start
    lon2, lat2, x2, y2 = end

    azimuth, _, length = geod.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(length) or length <= _MIN_SEGMENT_M:
        return None

    n = len(_SAMPLE_FRACTIONS)
    lons, lats, _ = geod.fwd(
        [lon1] * n, [lat1] * n, [azimuth] * n,
        [length * f for f in _SAMPLE_FRACTIONS],
    )
    xs, ys = transformer.transform(lons, lats)

    worst = 0.0
    midpoint: Optional[_Node] = None
    for fraction, lon, lat, x, y in zip(_SAMPLE_FRACTIONS, lons, lats, xs, ys):
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(
                f"the geodesic passes through ({lon:.6f}, {lat:.6f}), which has "
                f"no finite image in EPSG:{dst_epsg}"
            )
        if fraction == 0.5:
            midpoint = (lon, lat, x, y)
        worst = max(worst, _point_to_segment(x, y, x1, y1, x2, y2))

    assert midpoint is not None  # guaranteed by _SAMPLE_FRACTIONS
    return worst, midpoint


def _densify(start: _Node, end: _Node, geod: Geod, transformer: Transformer,
             tolerance: float, dst_epsg: int, out: List[Tuple[float, float]]) -> None:
    """Append the projected geodesic from ``start`` to ``end``, ``start`` excluded.

    Bisection is depth-first and left-to-right, so ``out`` stays ordered.  Only
    sub-segments that fail the tolerance test are split, which keeps the vertex
    count low on the easy parts of a line and concentrates it where the
    projection bends the geodesic hardest.
    """
    stack: List[Tuple[_Node, _Node, int]] = [(start, end, 0)]
    while stack:
        left, right, depth = stack.pop()

        verdict = None
        if depth < _MAX_DEPTH:
            verdict = _deviation(left, right, geod, transformer, dst_epsg)

        if verdict is None or verdict[0] <= tolerance:
            out.append((right[2], right[3]))
            continue

        middle = verdict[1]
        stack.append((middle, right, depth + 1))
        stack.append((left, middle, depth + 1))


def project_line(line: LineString, dst_epsg: int, *,
                 tolerance_m: float = DEFAULT_TOLERANCE_M) -> LineString:
    """Project a WGS84 line into ``dst_epsg``, tracing the geodesic course.

    Every pair of consecutive input vertices is joined by the shortest path on
    the WGS84 ellipsoid, densified until the straight segments of the returned
    geometry stay within ``tolerance_m`` of that path everywhere.  All original
    vertices are preserved; extra ones are inserted between them as needed.

    Parameters
    ----------
    line:
        ``LineString`` with longitude/latitude coordinates in EPSG:4326.  A Z
        dimension, if present, is dropped.
    dst_epsg:
        EPSG code of a projected CRS.
    tolerance_m:
        Maximum allowed deviation, in metres.  Defaults to 25 km.

    Returns
    -------
    LineString
        The projected line, always in easting/northing order regardless of the
        axis order the EPSG registry declares for ``dst_epsg``.

    Raises
    ------
    ValueError
        If ``dst_epsg`` is not a projected CRS, if ``tolerance_m`` is not
        positive, or if the line (or the geodesic between two of its vertices)
        leaves the valid domain of the target projection.

    Notes
    -----
    The deviation is measured in the target plane and converted to metres via
    the CRS axis unit, so where the projection inflates distances the check is
    conservative.  Where it shrinks them the measured error understates ground
    distance, but only by the projection's scale factor -- 0.04% for UTM, far
    inside the safety margin applied to the tolerance.
    """
    if not math.isfinite(tolerance_m) or tolerance_m <= 0.0:
        raise ValueError(f"tolerance_m must be a positive distance, got {tolerance_m!r}")

    coords = list(line.coords)
    if len(coords) < 2:
        return LineString()

    dst_epsg = int(dst_epsg)
    transformer, geod, unit = _projection(dst_epsg)
    tolerance = (tolerance_m * _SAFETY) / unit  # target CRS units

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    xs, ys = transformer.transform(lons, lats)

    nodes: List[_Node] = []
    for lon, lat, x, y in zip(lons, lats, xs, ys):
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(
                f"vertex ({lon:.6f}, {lat:.6f}) has no finite image in EPSG:{dst_epsg}"
            )
        nodes.append((lon, lat, x, y))

    out: List[Tuple[float, float]] = [(nodes[0][2], nodes[0][3])]
    for start, end in zip(nodes, nodes[1:]):
        _densify(start, end, geod, transformer, tolerance, dst_epsg, out)

    return LineString(out)
```