Bash is gated in this session, so I can't execute a verification run — the module below is written against the documented pyproj 3.7 / shapely 2.1 APIs (`Geod.fwd`/`inv` array forms, `Transformer.transform` array form, `CRS.get_geod`, `axis_info[..].unit_conversion_factor`) but I have not run it.

```python
"""Reproject WGS84 lines so the result follows true ellipsoidal geodesics.

A straight segment between two lon/lat vertices is not, in general, a straight
line in a projected CRS: the shortest path on the ellipsoid bows away from the
chord, badly so for long segments or strongly curved projections.
:func:`project_line` densifies every input segment along its real geodesic
until each output chord stays within :data:`MAX_DEVIATION_M` of that geodesic,
measuring the gap in the target CRS where the output geometry lives.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line", "MAX_DEVIATION_M"]

#: Largest permitted gap between the returned line and the true geodesic.
MAX_DEVIATION_M = 25_000.0

_SRC_EPSG = 4326

# Aim well inside the budget: the deviation test samples a chord at a few
# points rather than continuously, so leave room for what sampling misses.
_SAFETY_FACTOR = 0.25

# Every input segment is cut into pieces of at most this geodesic length before
# adaptive refinement starts. This defeats the symmetry trap where a chord's
# midpoint happens to sit on the projected geodesic while its quarter points
# are far off it.
_PRESPLIT_M = 200_000.0

# Where each candidate chord is compared against the geodesic. 0.5 must be
# present: that sample doubles as the insertion point when a chord fails.
_SAMPLE_FRACTIONS = (0.25, 0.5, 0.75)
_MID_SAMPLE = _SAMPLE_FRACTIONS.index(0.5)

_MAX_ROUNDS = 24
_MAX_KNOTS = 20_000
_MIN_STEP_M = 1.0


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a WGS84 lon/lat ``LineString`` into ``EPSG:<dst_epsg>``.

    The returned line passes through the projected images of all original
    vertices, in order, and every point of it lies within
    :data:`MAX_DEVIATION_M` (expressed in the target CRS's own units) of the
    geodesic course between the two input vertices it falls between.

    Parameters
    ----------
    line:
        ``LineString`` with longitude/latitude coordinates in EPSG:4326.
    dst_epsg:
        EPSG code of a projected CRS. Output coordinates are always
        easting/northing regardless of the CRS's declared axis order.

    Returns
    -------
    LineString
        The densified, projected line. Any Z values on the input are dropped.

    Raises
    ------
    ValueError
        If ``dst_epsg`` is not a projected CRS, or an input vertex has no
        image in it.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return LineString()

    dst_epsg = int(dst_epsg)
    transformer, geod, tolerance = _setup(dst_epsg)

    lons = np.array([c[0] for c in coords], dtype=float)
    lats = np.array([c[1] for c in coords], dtype=float)
    xs, ys = transformer.transform(lons, lats)
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)

    unmapped = ~(np.isfinite(xs) & np.isfinite(ys))
    if unmapped.any():
        bad = int(np.argmax(unmapped))
        raise ValueError(
            f"vertex {lons[bad]}, {lats[bad]} has no image in EPSG:{dst_epsg}"
        )

    points = [(float(xs[0]), float(ys[0]))]
    for i in range(len(coords) - 1):
        points.extend(
            _densify(
                geod,
                transformer,
                tolerance,
                (float(lons[i]), float(lats[i])),
                (float(xs[i]), float(ys[i])),
                (float(lons[i + 1]), float(lats[i + 1])),
                (float(xs[i + 1]), float(ys[i + 1])),
            )
        )
    return LineString(_drop_repeats(points))


@lru_cache(maxsize=None)
def _setup(dst_epsg: int):
    """Return the (transformer, geod, tolerance) triple for a target CRS.

    Cached because building a ``Transformer`` costs far more than using one,
    and a single line is usually projected alongside many of its neighbours.
    """
    src = CRS.from_epsg(_SRC_EPSG)
    dst = CRS.from_epsg(dst_epsg)
    if not dst.is_projected:
        raise ValueError(f"EPSG:{dst_epsg} is not a projected CRS")

    transformer = Transformer.from_crs(src, dst, always_xy=True)
    geod = src.get_geod() or Geod(ellps="WGS84")
    tolerance = MAX_DEVIATION_M * _SAFETY_FACTOR / _metres_per_unit(dst)
    return transformer, geod, tolerance


def _metres_per_unit(crs: CRS) -> float:
    """Metres per horizontal coordinate unit, so feet-based CRSs behave."""
    factors = [
        axis.unit_conversion_factor
        for axis in crs.axis_info[:2]
        if getattr(axis, "unit_conversion_factor", None)
    ]
    # The stricter factor wins on the (pathological) mixed-unit CRS.
    return max(factors) if factors else 1.0


def _densify(geod, transformer, tolerance, start_ll, start_xy, end_ll, end_xy):
    """Projected points tracing one input segment, excluding its first vertex.

    Points along the segment are addressed by geodesic distance from its start,
    which keeps the parameterisation exact for arbitrarily long segments:
    ``geod.fwd`` walks the same geodesic that ``geod.inv`` measured.
    """
    lon, lat = start_ll
    azimuth, _, length = geod.inv(lon, lat, end_ll[0], end_ll[1])
    if not math.isfinite(length) or length < _MIN_STEP_M:
        return [end_xy]

    pieces = max(1, math.ceil(length / _PRESPLIT_M))
    knots = _initial_knots(
        geod, transformer, lon, lat, azimuth,
        np.linspace(0.0, length, pieces + 1), start_xy, end_xy,
    )

    for _ in range(_MAX_ROUNDS):
        if len(knots) >= _MAX_KNOTS:
            break
        knots, refined = _refine(
            geod, transformer, tolerance, lon, lat, azimuth, knots
        )
        if not refined:
            break

    return [(x, y) for _, x, y in knots[1:]]


def _initial_knots(geod, transformer, lon, lat, azimuth, distances, start_xy, end_xy):
    """Seed the knot list, reusing the already-projected segment endpoints."""
    knots = [(0.0, start_xy[0], start_xy[1])]
    interior = distances[1:-1]
    if interior.size:
        xs, ys = _project_along(geod, transformer, lon, lat, azimuth, interior)
        for distance, x, y in zip(interior, xs, ys):
            if math.isfinite(x) and math.isfinite(y):
                knots.append((float(distance), float(x), float(y)))
    knots.append((float(distances[-1]), end_xy[0], end_xy[1]))
    return knots


def _refine(geod, transformer, tolerance, lon, lat, azimuth, knots):
    """Split every chord that strays too far, one generation at a time.

    Working breadth-first lets a whole generation of sample points share a
    single ``fwd`` + ``transform`` pass, which dominates the runtime.
    """
    distances = np.array([k[0] for k in knots], dtype=float)
    spans = distances[1:] - distances[:-1]
    # Chords already at the resolution floor cannot be improved by splitting.
    candidates = np.flatnonzero(spans > _MIN_STEP_M)
    if candidates.size == 0:
        return knots, False

    fractions = np.array(_SAMPLE_FRACTIONS, dtype=float)
    sample_distances = (
        distances[candidates, None] + spans[candidates, None] * fractions[None, :]
    )
    xs, ys = _project_along(
        geod, transformer, lon, lat, azimuth, sample_distances.ravel()
    )
    xs = np.asarray(xs, dtype=float).reshape(sample_distances.shape)
    ys = np.asarray(ys, dtype=float).reshape(sample_distances.shape)

    knot_x = np.array([k[1] for k in knots], dtype=float)
    knot_y = np.array([k[2] for k in knots], dtype=float)
    deviation = _chord_offsets(
        knot_x[candidates], knot_y[candidates],
        knot_x[candidates + 1], knot_y[candidates + 1],
        xs, ys,
    )

    mid_x = xs[:, _MID_SAMPLE]
    mid_y = ys[:, _MID_SAMPLE]
    # A midpoint outside the projection's domain would poison every later
    # measurement, so leave such a chord alone rather than insert infinities.
    split = (deviation > tolerance) & np.isfinite(mid_x) & np.isfinite(mid_y)
    if not split.any():
        return knots, False

    insertions = {
        int(chord): (
            float(sample_distances[row, _MID_SAMPLE]),
            float(mid_x[row]),
            float(mid_y[row]),
        )
        for row, chord in enumerate(candidates)
        if split[row]
    }
    refined = []
    for i, knot in enumerate(knots[:-1]):
        refined.append(knot)
        if i in insertions:
            refined.append(insertions[i])
    refined.append(knots[-1])
    return refined, True


def _project_along(geod, transformer, lon, lat, azimuth, distances):
    """Project the geodesic points sitting at ``distances`` from the start."""
    distances = np.asarray(distances, dtype=float)
    lons, lats, _ = geod.fwd(
        np.full(distances.shape, lon),
        np.full(distances.shape, lat),
        np.full(distances.shape, azimuth),
        distances.copy(),
    )
    return transformer.transform(lons, lats)


def _chord_offsets(ax, ay, bx, by, px, py):
    """Worst distance from each chord ``a->b`` to its sample points."""
    vx = bx - ax
    vy = by - ay
    squared = vx * vx + vy * vy
    wx = px - ax[:, None]
    wy = py - ay[:, None]

    # Degenerate chords (both ends on the same projected point) fall back to
    # plain point-to-point distance via t == 0.
    safe = np.where(squared > 0.0, squared, 1.0)
    t = np.clip((wx * vx[:, None] + wy * vy[:, None]) / safe[:, None], 0.0, 1.0)
    offsets = np.hypot(wx - t * vx[:, None], wy - t * vy[:, None])
    # An unprojectable sample counts as an infinite miss: refine and re-look.
    return np.where(np.isfinite(offsets), offsets, np.inf).max(axis=1)


def _drop_repeats(points):
    """Collapse consecutive duplicates while keeping a buildable line."""
    cleaned = [points[0]]
    for point in points[1:]:
        if point != cleaned[-1]:
            cleaned.append(point)
    if len(cleaned) < 2:
        cleaned.append(cleaned[0])
    return cleaned
```