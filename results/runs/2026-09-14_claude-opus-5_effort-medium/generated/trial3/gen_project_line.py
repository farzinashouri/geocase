"""Project a WGS84 (EPSG:4326) LineString into a projected CRS, densifying each
input segment so that the output polyline follows the true geodesic course.

The public entry point is :func:`project_line`.

Method
------
For every pair of consecutive input vertices the geodesic (shortest path on the
WGS84 ellipsoid) is sampled adaptively:

1. The segment is first cut into chunks of at most ``_CHUNK_M`` metres of
   geodesic length.  This defeats the symmetry traps that a purely midpoint
   driven refinement can fall into on very long segments (a chord whose
   midpoint error happens to vanish while the quarter points are far off).
2. Each chunk is then bisected recursively: the geodesic points at fractions
   0.25 / 0.5 / 0.75 of the chunk are projected and compared against the
   straight line joining the projected chunk endpoints.  If any of them lies
   further than ``_TOLERANCE_M`` from that straight line, the chunk is split in
   half and both halves are re-tested.

``_TOLERANCE_M`` is held well below the required 25 km so that the finite
sampling used by the test still leaves a comfortable margin.

Importing this module performs no I/O and creates no CRS objects; transformers
are built lazily on first use and cached per EPSG code.
"""

from __future__ import annotations

import math
from functools import lru_cache

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line"]

# Deviation budget, in metres on the ground, between the emitted polyline and
# the true geodesic.  The requirement is 25 km; we aim well inside it.
_TOLERANCE_M = 10_000.0

# Maximum geodesic length of a chunk before adaptive refinement starts.
_CHUNK_M = 1_000_000.0

# Guard against pathological recursion (e.g. a CRS that blows up locally).
_MAX_DEPTH = 18

# Fractions along a chunk at which the chord error is measured.
_PROBES = (0.25, 0.5, 0.75)


@lru_cache(maxsize=32)
def _projection(dst_epsg: int):
    """Return ``(transformer, metres_per_crs_unit)`` for ``dst_epsg``."""
    crs = CRS.from_epsg(int(dst_epsg))
    if crs.is_geographic:
        raise ValueError(f"EPSG:{dst_epsg} is a geographic CRS, not a projected one")

    factor = 1.0
    axes = getattr(crs, "axis_info", None)
    if axes:
        unit_factor = getattr(axes[0], "unit_conversion_factor", None)
        if unit_factor:
            factor = float(unit_factor)

    transformer = Transformer.from_crs(CRS.from_epsg(4326), crs, always_xy=True)
    return transformer, factor


@lru_cache(maxsize=1)
def _geod() -> Geod:
    return Geod(ellps="WGS84")


def _point_to_segment_distance(px, py, ax, ay, bx, by) -> float:
    """Distance from ``(px, py)`` to the segment ``(ax, ay)-(bx, by)``."""
    dx = bx - ax
    dy = by - ay
    denom = dx * dx + dy * dy
    if denom == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / denom
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _finite(xy) -> bool:
    return math.isfinite(xy[0]) and math.isfinite(xy[1])


def _densify_segment(lon1, lat1, lon2, lat2, transformer, factor, out):
    """Append the projected geodesic from vertex 1 to vertex 2 to ``out``.

    The starting point is assumed to be already present in ``out``; the end
    point is appended by this call.
    """
    geod = _geod()
    az12, _az21, total = geod.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(total) or total == 0.0:
        out.append(transformer.transform(lon2, lat2))
        return

    tol = _TOLERANCE_M / factor  # tolerance expressed in CRS units

    def geodesic_at(distance):
        lon, lat, _ = geod.fwd(lon1, lat1, az12, distance)
        return lon, lat

    def projected_at(distance):
        lon, lat = geodesic_at(distance)
        return transformer.transform(lon, lat)

    n_chunks = max(1, int(math.ceil(total / _CHUNK_M)))
    chunk = total / n_chunks

    for i in range(n_chunks):
        d0 = i * chunk
        d1 = total if i == n_chunks - 1 else (i + 1) * chunk
        p0 = out[-1] if i == 0 else projected_at(d0)
        p1 = transformer.transform(lon2, lat2) if i == n_chunks - 1 else projected_at(d1)

        # Iterative depth-first bisection over [d0, d1].
        stack = [(d0, d1, p0, p1, 0)]
        while stack:
            a, b, pa, pb, depth = stack.pop()

            if depth >= _MAX_DEPTH:
                out.append(pb)
                continue

            worst = 0.0
            probes = []
            for t in _PROBES:
                d = a + (b - a) * t
                p = projected_at(d)
                probes.append((d, p))
                if not (_finite(p) and _finite(pa) and _finite(pb)):
                    worst = math.inf
                    break
                err = _point_to_segment_distance(p[0], p[1], pa[0], pa[1], pb[0], pb[1])
                if err > worst:
                    worst = err

            if worst <= tol:
                out.append(pb)
                continue

            mid_d, mid_p = probes[1] if len(probes) > 1 else (
                (a + b) / 2.0,
                projected_at((a + b) / 2.0),
            )
            # Push the far half first so the near half is processed next.
            stack.append((mid_d, b, mid_p, pb, depth + 1))
            stack.append((a, mid_d, pa, mid_p, depth + 1))


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a WGS84 ``LineString`` into ``dst_epsg``, following geodesics.

    Parameters
    ----------
    line:
        A shapely ``LineString`` whose coordinates are ``(longitude, latitude)``
        in EPSG:4326.
    dst_epsg:
        EPSG code of a projected CRS.

    Returns
    -------
    LineString
        The line in ``dst_epsg``, densified so that it never departs from the
        projected geodesic course by more than 25 km.  Any Z values on the
        input are dropped.
    """
    if not isinstance(line, LineString):
        raise TypeError("line must be a shapely LineString")
    if line.is_empty:
        return LineString()

    coords = [(float(c[0]), float(c[1])) for c in line.coords]
    transformer, factor = _projection(int(dst_epsg))

    out = [transformer.transform(coords[0][0], coords[0][1])]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        if lon1 == lon2 and lat1 == lat2:
            continue
        _densify_segment(lon1, lat1, lon2, lat2, transformer, factor, out)

    # Drop duplicate neighbours and anything the projection sent to infinity.
    cleaned = []
    for p in out:
        if not _finite(p):
            continue
        if cleaned and cleaned[-1] == p:
            continue
        cleaned.append(p)

    if len(cleaned) < 2:
        raise ValueError(
            f"line does not project to a valid geometry in EPSG:{dst_epsg}"
        )
    return LineString(cleaned)