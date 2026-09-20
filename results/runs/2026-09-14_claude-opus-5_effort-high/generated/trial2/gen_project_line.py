"""Project a WGS84 ``LineString`` into a projected CRS along geodesic paths.

A straight segment between two vertices of a WGS84 line is a *rhumb-like*
artefact of the coordinate space, not the shortest path on the ellipsoid, and
projecting only the original vertices bakes that artefact into the result.
:func:`project_line` instead densifies every input segment along its geodesic
and refines it until the output polyline stays within 25 km of the projected
geodesic everywhere.

Densification happens in two passes:

1. a uniform pass that drops a vertex at least every 100 km of geodesic
   distance, which alone bounds the error at a few hundred metres for any
   sanely-scaled projection, and
2. an adaptive bisection pass that measures, *in target-CRS units*, how far the
   geodesic midpoint of each candidate segment falls from that segment's chord
   and splits until the deviation is comfortably inside the tolerance.

Measuring in target-CRS units is the point of pass 2: it is what makes the
guarantee survive regions where the projection's scale factor is large (a line
near the pole in EPSG:3857, or one far outside its UTM zone), where a small
ground error corresponds to a large error on the map.

Limitations: near a projection's singularity (e.g. the pole in a Mercator, the
antipode of a transverse Mercator's central meridian) the projected geodesic is
unbounded and no finite vertex count can honour the tolerance; refinement there
is capped by :data:`_MAX_DEPTH` and :data:`_MIN_SEGMENT_M` and returns the best
available approximation. Vertices that the target CRS cannot represent at all
are dropped.
"""

from __future__ import annotations

import math
from functools import lru_cache

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line", "TOLERANCE_M"]

#: Required fidelity of the output to the true projected geodesic.
TOLERANCE_M = 25_000.0

# Refinement targets a fraction of the budget: the midpoint test samples the
# deviation at one point per segment, so the true maximum over the segment can
# sit somewhat above the measured value.
_REFINE_TARGET_M = TOLERANCE_M / 4.0

# Uniform pre-densification step, in geodesic metres.
_INITIAL_STEP_M = 100_000.0
_MAX_INITIAL_STEPS = 10_000

# Termination guards for the adaptive pass.
_MAX_DEPTH = 20
_MIN_SEGMENT_M = 100.0

_SOURCE_EPSG = 4326


@lru_cache(maxsize=1)
def _geod() -> Geod:
    return Geod(ellps="WGS84")


@lru_cache(maxsize=32)
def _target(dst_epsg: int):
    """Return ``(transformer, metres_per_crs_unit)`` for ``dst_epsg``."""
    crs = CRS.from_epsg(dst_epsg)
    if not crs.is_projected:
        raise ValueError(f"EPSG:{dst_epsg} is not a projected CRS")
    transformer = Transformer.from_crs(
        CRS.from_epsg(_SOURCE_EPSG), crs, always_xy=True
    )
    metres_per_unit = crs.axis_info[0].unit_conversion_factor or 1.0
    return transformer, float(metres_per_unit)


def _finite(xy) -> bool:
    return math.isfinite(xy[0]) and math.isfinite(xy[1])


def _chord_distance(p, a, b, metres_per_unit: float) -> float:
    """Distance in metres from point ``p`` to the segment ``a``-``b``."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx = bx - ax
    dy = by - ay
    denom = dx * dx + dy * dy
    if denom == 0.0:
        return math.hypot(px - ax, py - ay) * metres_per_unit
    t = ((px - ax) * dx + (py - ay) * dy) / denom
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)) * metres_per_unit


def _geodesic_length(geod: Geod, a, b) -> float:
    return float(geod.inv(a[0], a[1], b[0], b[1])[2])


def _geodesic_midpoint(geod: Geod, a, b):
    """Midpoint of the geodesic ``a``-``b``, or ``None`` if not worth taking."""
    length = _geodesic_length(geod, a, b)
    if not math.isfinite(length) or length <= _MIN_SEGMENT_M:
        return None
    points = geod.npts(a[0], a[1], b[0], b[1], 1)
    if not points:
        return None
    return (float(points[0][0]), float(points[0][1]))


def _uniform_geodesic_points(geod: Geod, a, b):
    """``a``, ``b`` plus evenly spaced geodesic points no more than a step apart."""
    length = _geodesic_length(geod, a, b)
    if not math.isfinite(length) or length <= _INITIAL_STEP_M:
        return [a, b]
    steps = min(int(math.ceil(length / _INITIAL_STEP_M)), _MAX_INITIAL_STEPS)
    interior = geod.npts(a[0], a[1], b[0], b[1], steps - 1)
    return [a] + [(float(lon), float(lat)) for lon, lat in interior] + [b]


def _refine(geod, transformer, metres_per_unit, a_ll, a_xy, b_ll, b_xy, out):
    """Append projected vertices for ``a``-``b``, excluding the ``b`` endpoint."""
    # LIFO stack, pushing the right half first so the left half pops first and
    # vertices land in ``out`` in along-line order.
    stack = [(a_ll, a_xy, b_ll, b_xy, 0)]
    while stack:
        a_ll, a_xy, b_ll, b_xy, depth = stack.pop()

        if depth >= _MAX_DEPTH or not (_finite(a_xy) and _finite(b_xy)):
            out.append(a_xy)
            continue

        mid_ll = _geodesic_midpoint(geod, a_ll, b_ll)
        if mid_ll is None:
            out.append(a_xy)
            continue

        mid_xy = transformer.transform(mid_ll[0], mid_ll[1])
        if not _finite(mid_xy):
            # The midpoint is outside the CRS's representable domain; splitting
            # further cannot produce a usable vertex here.
            out.append(a_xy)
            continue

        if _chord_distance(mid_xy, a_xy, b_xy, metres_per_unit) <= _REFINE_TARGET_M:
            out.append(a_xy)
            continue

        stack.append((mid_ll, mid_xy, b_ll, b_xy, depth + 1))
        stack.append((a_ll, a_xy, mid_ll, mid_xy, depth + 1))


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a WGS84 line into ``dst_epsg``, following geodesics.

    Parameters
    ----------
    line:
        A :class:`shapely.geometry.LineString` whose coordinates are
        longitude/latitude degrees in EPSG:4326. Any Z ordinates are dropped.
    dst_epsg:
        EPSG code of a projected CRS.

    Returns
    -------
    LineString
        The line in ``dst_epsg``, densified so that it stays within
        :data:`TOLERANCE_M` of the projected geodesic joining each pair of
        consecutive input vertices.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected a LineString, got {type(line).__name__}")
    if line.is_empty:
        return LineString()

    transformer, metres_per_unit = _target(int(dst_epsg))
    geod = _geod()

    # Collapse repeated input vertices; they carry no geodesic to trace.
    vertices = []
    for coord in line.coords:
        vertex = (float(coord[0]), float(coord[1]))
        if not vertices or vertex != vertices[-1]:
            vertices.append(vertex)

    if len(vertices) == 1:
        xy = transformer.transform(*vertices[0])
        if not _finite(xy):
            raise ValueError(f"line cannot be represented in EPSG:{dst_epsg}")
        return LineString([xy, xy])

    projected: list = []
    last_xy = None
    for start, end in zip(vertices, vertices[1:]):
        dense_ll = _uniform_geodesic_points(geod, start, end)
        xs, ys = transformer.transform(
            [lon for lon, _ in dense_ll], [lat for _, lat in dense_ll]
        )
        dense_xy = [(float(x), float(y)) for x, y in zip(xs, ys)]
        for i in range(len(dense_ll) - 1):
            _refine(
                geod,
                transformer,
                metres_per_unit,
                dense_ll[i],
                dense_xy[i],
                dense_ll[i + 1],
                dense_xy[i + 1],
                projected,
            )
        last_xy = dense_xy[-1]
    projected.append(last_xy)

    coords = []
    for xy in projected:
        if not _finite(xy):
            continue
        if not coords or xy != coords[-1]:
            coords.append(xy)

    if len(coords) < 2:
        raise ValueError(f"line cannot be represented in EPSG:{dst_epsg}")
    return LineString(coords)