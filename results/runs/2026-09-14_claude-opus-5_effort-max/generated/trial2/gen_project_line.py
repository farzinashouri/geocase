"""Geodesic-faithful reprojection of WGS84 lines into a projected CRS.

A segment between two lon/lat vertices does not stay straight when it is
projected: the shortest path on the ellipsoid -- the geodesic -- maps to a
curve in a projected CRS.  :func:`project_line` therefore densifies every
input segment with points taken from the true geodesic, adding just enough of
them that the returned polyline never strays further than
:data:`TOLERANCE_METRES` from that curve.

Importing this module has no side effects: PROJ objects are built lazily on
first use and then cached.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Tuple

import numpy as np
from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line", "TOLERANCE_METRES"]

#: Largest permitted deviation of the returned polyline from the projected
#: geodesic, in metres.
TOLERANCE_METRES = 25_000.0

_SOURCE_EPSG = 4326

# Curve samples are taken at the quarter points of every candidate output
# segment.  Testing three interior points rather than only the midpoint keeps
# the test honest for curves with an inflection near their middle, where the
# midpoint can sit on the chord while the curve bulges to either side of it.
_SAMPLE_FRACTIONS = np.array([0.25, 0.5, 0.75])

# The samples only bound the deviation where they are taken, so refinement
# aims at a fraction of the real budget to leave headroom in between.
_SAFETY_FACTOR = 0.5

# Every input segment is first cut into pieces of at most this geodesic
# length.  This is cheap (200 vertices for a line right around the globe) and
# gives the adaptive pass a starting point free of accidental symmetries.
_INITIAL_STEP_METRES = 200_000.0
_MAX_INITIAL_PIECES = 4096

# Backstops for the adaptive pass.  A projection seam (a geodesic crossing the
# antimeridian of a world Mercator, say) maps the geodesic to a *discontinuous*
# curve that no polyline can follow, so the error test can never be satisfied
# there; refinement stops rather than subdividing forever.
_MAX_ROUNDS = 16
_MAX_VERTICES = 250_000


@lru_cache(maxsize=1)
def _wgs84_geod() -> Geod:
    """The WGS84 ellipsoid, on which the input coordinates are defined."""
    return Geod(ellps="WGS84")


@lru_cache(maxsize=32)
def _target(dst_epsg: int) -> Tuple[Transformer, float]:
    """Transformer into ``dst_epsg`` and its linear unit in metres."""
    crs = CRS.from_epsg(dst_epsg)
    if not crs.is_projected:
        raise ValueError(
            f"EPSG:{dst_epsg} ({crs.name}) is not a projected CRS; "
            "project_line needs a CRS with linear coordinates"
        )
    transformer = Transformer.from_crs(
        CRS.from_epsg(_SOURCE_EPSG), crs, always_xy=True
    )
    # Not every projected CRS is in metres (EPSG:2263 is in US survey feet),
    # so the tolerance has to be expressed in the CRS's own units.
    factor = float(getattr(crs.axis_info[0], "unit_conversion_factor", 1.0) or 1.0)
    if not np.isfinite(factor) or factor <= 0.0:
        factor = 1.0
    return transformer, factor


def _f64(values: np.ndarray) -> np.ndarray:
    """A private float64 copy: pyproj may transform arrays in place."""
    return np.array(values, dtype=np.float64)


def _project(
    transformer: Transformer, lons: np.ndarray, lats: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Project lon/lat arrays, yielding infinities outside the CRS's domain."""
    xx, yy = transformer.transform(_f64(lons), _f64(lats), errcheck=False)
    return np.asarray(xx, dtype=float), np.asarray(yy, dtype=float)


def _geodesic_points(
    geod: Geod,
    lon0: np.ndarray,
    lat0: np.ndarray,
    azimuth: np.ndarray,
    length: np.ndarray,
    fraction: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Points a given fraction of the way along each geodesic.

    Walking ``fraction * length`` from the start point along the geodesic's
    initial azimuth lands exactly on the geodesic, so this is an exact
    parametrisation of it rather than an interpolation.
    """
    lons, lats, _ = geod.fwd(
        _f64(lon0), _f64(lat0), _f64(azimuth), _f64(length * fraction)
    )
    return np.asarray(lons, dtype=float), np.asarray(lats, dtype=float)


def _chord_error(
    xa: np.ndarray,
    ya: np.ndarray,
    xb: np.ndarray,
    yb: np.ndarray,
    px: np.ndarray,
    py: np.ndarray,
) -> np.ndarray:
    """Largest distance from each interval's curve samples to its chord.

    ``xa .. yb`` are ``(n,)`` chord endpoints, ``px``/``py`` are ``(n, k)``
    samples of the projected geodesic between them.
    """
    dx = (xb - xa)[:, None]
    dy = (yb - ya)[:, None]
    wx = px - xa[:, None]
    wy = py - ya[:, None]

    squared = dx * dx + dy * dy
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        along = np.where(
            squared > 0.0,
            (wx * dx + wy * dy) / np.where(squared > 0.0, squared, 1.0),
            0.0,
        )
        along = np.clip(along, 0.0, 1.0)
        distance = np.hypot(wx - along * dx, wy - along * dy)

    # A non-finite sample means the projection is undefined on this interval.
    # Subdividing cannot fix that, so report no error and let it be accepted.
    return np.where(np.isfinite(distance), distance, 0.0).max(axis=1)


def _densified_track(
    geod: Geod,
    transformer: Transformer,
    lon: np.ndarray,
    lat: np.ndarray,
    tolerance: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Projected vertices tracing the geodesics through ``lon``/``lat``.

    The work is done on a flat, globally ordered list of intervals; each one
    carries the parent segment it belongs to, its parameter range within that
    segment and its projected endpoints.  Refining means replacing an interval
    by the four pieces cut out by its own curve samples, which keeps every
    round a handful of vectorised pyproj calls no matter how many input
    segments there are.
    """
    azimuth, _, length = geod.inv(
        _f64(lon[:-1]), _f64(lat[:-1]), _f64(lon[1:]), _f64(lat[1:])
    )
    azimuth = np.nan_to_num(np.asarray(azimuth, dtype=float), nan=0.0)
    length = np.nan_to_num(np.asarray(length, dtype=float), nan=0.0, posinf=0.0)
    lon0, lat0 = lon[:-1], lat[:-1]
    n_segments = lon0.size

    # Projected input vertices; reused verbatim at both ends of every segment
    # so that the joins stay exact and the input vertices survive unmoved.
    vertex_x, vertex_y = _project(transformer, lon, lat)

    pieces = np.clip(
        np.ceil(length / _INITIAL_STEP_METRES).astype(np.int64),
        1,
        _MAX_INITIAL_PIECES,
    )
    parent = np.repeat(np.arange(n_segments), pieces)
    index = np.arange(parent.size) - np.repeat(np.cumsum(pieces) - pieces, pieces)
    per_segment = pieces[parent].astype(float)
    t_start = index / per_segment
    t_end = (index + 1) / per_segment

    x_start, y_start = _project(
        transformer,
        *_geodesic_points(
            geod, lon0[parent], lat0[parent], azimuth[parent], length[parent], t_start
        ),
    )
    x_end, y_end = _project(
        transformer,
        *_geodesic_points(
            geod, lon0[parent], lat0[parent], azimuth[parent], length[parent], t_end
        ),
    )
    opens = index == 0
    closes = index == pieces[parent] - 1
    x_start[opens] = vertex_x[parent[opens]]
    y_start[opens] = vertex_y[parent[opens]]
    x_end[closes] = vertex_x[parent[closes] + 1]
    y_end[closes] = vertex_y[parent[closes] + 1]

    n_samples = _SAMPLE_FRACTIONS.size
    accepted = np.zeros(parent.size, dtype=bool)
    for _ in range(_MAX_ROUNDS):
        pending = np.flatnonzero(~accepted)
        if pending.size == 0 or parent.size >= _MAX_VERTICES:
            break

        sample_t = (
            t_start[pending, None]
            + (t_end - t_start)[pending, None] * _SAMPLE_FRACTIONS[None, :]
        )
        flat = np.repeat(parent[pending], n_samples)
        sample_x, sample_y = _project(
            transformer,
            *_geodesic_points(
                geod,
                lon0[flat],
                lat0[flat],
                azimuth[flat],
                length[flat],
                sample_t.ravel(),
            ),
        )
        sample_x = sample_x.reshape(sample_t.shape)
        sample_y = sample_y.reshape(sample_t.shape)

        error = _chord_error(
            x_start[pending],
            y_start[pending],
            x_end[pending],
            y_end[pending],
            sample_x,
            sample_y,
        )
        splits = error > tolerance
        if not splits.any():
            break

        n_intervals = parent.size
        splitting = np.zeros(n_intervals, dtype=bool)
        splitting[pending] = splits

        # Interior columns of intervals that are not splitting are never read.
        rows = pending[splits]
        interior_t = np.zeros((n_intervals, n_samples))
        interior_x = np.zeros((n_intervals, n_samples))
        interior_y = np.zeros((n_intervals, n_samples))
        interior_t[rows] = sample_t[splits]
        interior_x[rows] = sample_x[splits]
        interior_y[rows] = sample_y[splits]
        bound_t = np.column_stack([t_start, interior_t, t_end])
        bound_x = np.column_stack([x_start, interior_x, x_end])
        bound_y = np.column_stack([y_start, interior_y, y_end])
        last = n_samples + 1

        counts = np.where(splitting, n_samples + 1, 1)
        source = np.repeat(np.arange(n_intervals), counts)
        offset = np.arange(counts.sum()) - np.repeat(
            np.cumsum(counts) - counts, counts
        )
        is_child = splitting[source]
        lower = offset
        upper = np.where(is_child, offset + 1, last)

        parent = parent[source]
        t_start, t_end = bound_t[source, lower], bound_t[source, upper]
        x_start, x_end = bound_x[source, lower], bound_x[source, upper]
        y_start, y_end = bound_y[source, lower], bound_y[source, upper]
        accepted = ~is_child

    # Consecutive intervals share an endpoint, bit for bit, so the polyline is
    # the first interval's start followed by every interval's end.
    return (
        np.concatenate([x_start[:1], x_end]),
        np.concatenate([y_start[:1], y_end]),
    )


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a WGS84 line into ``dst_epsg``, following geodesics.

    Each segment of ``line`` is treated as the geodesic (shortest path on the
    WGS84 ellipsoid) between its two vertices, and is returned as however many
    straight pieces it takes for the result to stay within
    :data:`TOLERANCE_METRES` of that geodesic's image in the target CRS.  The
    input vertices are preserved exactly; only extra vertices are added.

    Parameters
    ----------
    line:
        A :class:`~shapely.geometry.LineString` whose coordinates are
        longitude/latitude degrees in EPSG:4326.  Any Z values are dropped.
    dst_epsg:
        EPSG code of a projected CRS.

    Returns
    -------
    shapely.geometry.LineString
        The densified line, in the coordinates and linear units of
        ``dst_epsg``.

    Raises
    ------
    ValueError
        If ``line`` is empty, if its latitudes are not in [-90, 90], if
        ``dst_epsg`` is not a projected CRS, or if fewer than two of the
        resulting vertices fall inside that CRS's domain.

    Notes
    -----
    The 25 km guarantee is a cross-track deviation measured in the projected
    plane, converted into the CRS's own linear unit, and it holds where the
    projection is defined and continuous.  Vertices that PROJ cannot represent
    (beyond a Mercator's latitude limit, for instance) are dropped, and a
    geodesic crossing a projection seam such as a world Mercator's
    antimeridian maps to a curve that is discontinuous in the plane -- no
    polyline can trace that, so the result simply jumps across the seam.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected a LineString, got {type(line).__name__}")
    if line.is_empty:
        raise ValueError("cannot project an empty LineString")

    coords = np.asarray(line.coords, dtype=float)[:, :2]
    if coords.shape[0] < 2:
        raise ValueError("a line needs at least two vertices")
    lon, lat = coords[:, 0], coords[:, 1]
    if np.any(np.abs(lat) > 90.0):
        raise ValueError(
            "latitudes outside [-90, 90]; coordinates must be (longitude, latitude)"
        )

    transformer, unit_in_metres = _target(int(dst_epsg))
    tolerance = _SAFETY_FACTOR * TOLERANCE_METRES / unit_in_metres

    xs, ys = _densified_track(_wgs84_geod(), transformer, lon, lat, tolerance)

    points = np.column_stack([xs, ys])
    points = points[np.isfinite(points).all(axis=1)]
    if points.shape[0] < 2:
        raise ValueError(
            f"the line cannot be represented in EPSG:{dst_epsg}: "
            "fewer than two vertices fall inside its domain"
        )

    keep = np.ones(points.shape[0], dtype=bool)
    keep[1:] = np.any(points[1:] != points[:-1], axis=1)
    points = points[keep]
    if points.shape[0] < 2:
        # Every vertex of the input projected to the same place.
        points = np.repeat(points, 2, axis=0)

    return LineString(points)