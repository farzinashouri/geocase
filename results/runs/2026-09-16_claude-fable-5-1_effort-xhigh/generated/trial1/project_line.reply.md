```python
"""Project a WGS84 LineString into a projected CRS along geodesic courses.

The straight segments of the input are interpreted as geodesics (shortest
paths on the WGS84 ellipsoid) rather than as straight lines of the target
projection.  :func:`project_line` samples each geodesic densely, projects the
samples, and then splits any span whose straight projected chord would still
stray from the projected geodesic, so the returned polyline follows the
geodesic course to well within 25 km everywhere along its length.
"""

from __future__ import annotations

import math
import operator

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

Point = tuple[float, float]

#: Largest departure from the geodesic course, in metres, that the output of
#: :func:`project_line` may show anywhere along its length.
TOLERANCE_M = 25_000.0

# Consecutive geodesic samples are never further apart than this along the
# ellipsoid.  Chords this short cannot leave the geodesic by more than a few
# kilometres in any well-behaved projection, which leaves only regions of
# extreme distortion (e.g. Mercator near the poles) to the refinement step.
_MAX_SPACING_M = 10_000.0

# Fraction of TOLERANCE_M by which a chord's midpoint may miss the projected
# geodesic before the chord is split.  A midpoint test only estimates the true
# maximum deviation, hence the generous safety margin.
_SAGITTA_FRACTION = 0.1

# Cap on recursive splitting so that pathological spans (a projection
# singularity, a discontinuity such as the antimeridian of a world map) cannot
# generate unbounded numbers of vertices.
_MAX_DEPTH = 10


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Return ``line`` expressed in ``EPSG:dst_epsg``, following geodesic courses.

    Parameters
    ----------
    line
        LineString with longitude/latitude coordinates in EPSG:4326.  A third
        coordinate, if present, is ignored.
    dst_epsg
        EPSG code of the projected target coordinate reference system.

    Returns
    -------
    shapely.LineString
        2-D LineString in the target CRS.  Its vertices lie on the geodesics
        joining consecutive input vertices (the input vertices themselves are
        kept, projected exactly) and its straight segments stay within
        :data:`TOLERANCE_M` of those geodesics.

    Notes
    -----
    On world-wide cylindrical projections a course that crosses the
    antimeridian necessarily jumps across the map; the line is not split.
    """
    vertices = [(float(c[0]), float(c[1])) for c in line.coords]
    if not vertices:
        return LineString()

    dst_crs = _target_crs(dst_epsg)
    geod = Geod(ellps="WGS84")
    transformer = Transformer.from_crs(CRS.from_epsg(4326), dst_crs, always_xy=True)
    tol = _SAGITTA_FRACTION * TOLERANCE_M / _metres_per_unit(dst_crs)

    def project(lon: float, lat: float) -> Point:
        x, y = transformer.transform(lon, lat)
        return float(x), float(y)

    out: list[Point] = [project(*vertices[0])]
    for (lon1, lat1), (lon2, lat2) in zip(vertices[:-1], vertices[1:]):
        az12, _, dist = geod.inv(lon1, lat1, lon2, lat2)
        arc = _Arc(geod, transformer, lon1, lat1, az12, tol)

        # Sample at half the maximum spacing so that every piece comes with
        # its own midpoint for the chord test below.
        n_pieces = max(1, math.ceil(dist / _MAX_SPACING_M))
        half_step = dist / (2 * n_pieces)
        samples = [project(lon1, lat1)]
        samples += arc.points([k * half_step for k in range(1, 2 * n_pieces)])
        samples.append(project(lon2, lat2))

        for i in range(n_pieces):
            a, m, b = samples[2 * i], samples[2 * i + 1], samples[2 * i + 2]
            if _chord_deviation(m, a, b) > tol:
                s_a = 2 * i * half_step
                s_m = s_a + half_step
                s_b = s_m + half_step
                _refine(arc, s_a, s_m, a, m, 1, out)
                out.append(m)
                _refine(arc, s_m, s_b, m, b, 1, out)
            out.append(b)

    return LineString(out)


class _Arc:
    """A geodesic leaving ``(lon0, lat0)`` with forward azimuth ``az0``.

    Points along the arc are addressed by their distance ``s`` in metres from
    the start and are returned already projected into the target CRS.
    ``tol`` is the chord tolerance in target-CRS units.
    """

    __slots__ = ("_geod", "_transformer", "_lon0", "_lat0", "_az0", "tol")

    def __init__(
        self,
        geod: Geod,
        transformer: Transformer,
        lon0: float,
        lat0: float,
        az0: float,
        tol: float,
    ) -> None:
        self._geod = geod
        self._transformer = transformer
        self._lon0 = lon0
        self._lat0 = lat0
        self._az0 = az0
        self.tol = tol

    def point(self, s: float) -> Point:
        lon, lat, _ = self._geod.fwd(self._lon0, self._lat0, self._az0, s)
        x, y = self._transformer.transform(lon, lat)
        return float(x), float(y)

    def points(self, distances: list[float]) -> list[Point]:
        n = len(distances)
        lons, lats, _ = self._geod.fwd(
            [self._lon0] * n, [self._lat0] * n, [self._az0] * n, list(distances)
        )
        xs, ys = self._transformer.transform(lons, lats)
        return [(float(x), float(y)) for x, y in zip(xs, ys)]


def _refine(
    arc: _Arc,
    s_a: float,
    s_b: float,
    a: Point,
    b: Point,
    depth: int,
    out: list[Point],
) -> None:
    """Append the projected points strictly between ``s_a`` and ``s_b`` on ``arc``
    that are needed for straight chords to stay within ``arc.tol`` of the
    projected geodesic.  ``a`` and ``b`` are the projected ends of the span.
    """
    if depth >= _MAX_DEPTH:
        return
    s_m = 0.5 * (s_a + s_b)
    m = arc.point(s_m)
    if _chord_deviation(m, a, b) <= arc.tol:
        return
    _refine(arc, s_a, s_m, a, m, depth + 1, out)
    out.append(m)
    _refine(arc, s_m, s_b, m, b, depth + 1, out)


def _chord_deviation(p: Point, a: Point, b: Point) -> float:
    """Distance from ``p`` to the straight segment ``a``-``b``.

    Non-finite coordinates mean a point fell outside the projection's domain;
    splitting cannot fix that, so such spans report no deviation.
    """
    (px, py), (ax, ay), (bx, by) = p, a, b
    if not all(map(math.isfinite, (px, py, ax, ay, bx, by))):
        return 0.0
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    t = min(1.0, max(0.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _metres_per_unit(crs: CRS) -> float:
    """Length of one horizontal unit of ``crs`` in metres (1.0 if unknown)."""
    for axis in crs.axis_info:
        factor = axis.unit_conversion_factor
        if factor and factor > 0:
            return float(factor)
    return 1.0


def _target_crs(dst_epsg) -> CRS:
    """Build the target CRS from an EPSG code (any integer type), falling back
    to whatever pyproj can interpret for other inputs."""
    try:
        code = operator.index(dst_epsg)
    except TypeError:
        return CRS.from_user_input(dst_epsg)
    return CRS.from_epsg(code)
```