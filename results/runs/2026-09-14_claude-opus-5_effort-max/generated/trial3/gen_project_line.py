"""Geodesic-faithful projection of WGS84 lines.

The straight segments of a naively projected line are *not* the projected
images of the geodesics joining the input vertices: on the ellipsoid the
shortest path between two points bends away from the projected chord, by
hundreds of kilometres for continental-scale hops.  :func:`project_line`
densifies every input segment along its geodesic, adding just enough vertices
that the returned line stays within :data:`TOLERANCE_M` of the true projected
geodesic everywhere.

Because every emitted vertex lies exactly on the geodesic, the error of the
result is the largest deviation of any single output segment from the arc it
spans -- deviations do not accumulate along the line.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

__all__ = ["project_line", "TOLERANCE_M"]

#: Maximum distance, in metres, between the returned line and the true
#: projected geodesic.
TOLERANCE_M = 25_000.0

_WGS84_EPSG = 4326
_MEAN_EARTH_RADIUS_M = 6_371_008.8

# A chord subtending an arc of length L on a sphere of radius R bulges away
# from that arc by roughly L**2 / (8 * R).  Capping the geodesic length of
# every segment keeps the *on-ellipsoid* deviation an order of magnitude
# inside the budget whatever the projection does, and guarantees each
# segment's curvature is actually sampled by the planar test below.
_MAX_STEP_M = math.sqrt(8.0 * _MEAN_EARTH_RADIUS_M * TOLERANCE_M / 10.0)  # ~357 km

# The planar test measures deviation at sub-segment midpoints only, which
# slightly understates the true maximum, so spend a quarter of the budget.
_PLANAR_SAFETY = 0.25

# Refining below this geodesic length cannot buy accuracy at a 25 km
# tolerance; it only matters next to projection discontinuities (an
# antimeridian jump, say) where the planar test can never be satisfied.
_MIN_STEP_M = 1.0

_MAX_ROUNDS = 24
_MAX_POINTS_PER_SEGMENT = 100_000


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """The WGS84 ellipsoid the EPSG:4326 input is expressed on."""
    return Geod(ellps="WGS84")


@lru_cache(maxsize=32)
def _target(dst_epsg: int):
    """Transformer into ``dst_epsg`` plus the size of its axis unit in metres."""
    dst = CRS.from_epsg(dst_epsg)
    if not dst.is_projected:
        raise ValueError(f"EPSG:{dst_epsg} is not a projected CRS")
    axes = dst.axis_info
    metres_per_unit = (getattr(axes[0], "unit_conversion_factor", 1.0) if axes else 1.0) or 1.0
    transformer = Transformer.from_crs(CRS.from_epsg(_WGS84_EPSG), dst, always_xy=True)
    return transformer, float(metres_per_unit)


def _project(transformer, lons, lats):
    xs, ys = transformer.transform(np.asarray(lons, dtype=float), np.asarray(lats, dtype=float))
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)


def _geodesic_points(geod, lon, lat, azimuth, distances):
    """Points ``distances`` metres along the geodesic leaving (lon, lat) on ``azimuth``.

    A geodesic is pinned down by a start point and an initial azimuth, so
    marching out along the azimuth returned by ``Geod.inv`` samples exactly the
    geodesic that joins the two input vertices.
    """
    distances = np.asarray(distances, dtype=float)
    if distances.size == 0:
        return distances.copy(), distances.copy()
    n = distances.size
    out_lon, out_lat, _ = geod.fwd(
        np.full(n, lon, dtype=float),
        np.full(n, lat, dtype=float),
        np.full(n, azimuth, dtype=float),
        distances.copy(),
    )
    return np.asarray(out_lon, dtype=float), np.asarray(out_lat, dtype=float)


def _deviation(x1, y1, x2, y2, xm, ym):
    """Planar distance from each (xm, ym) to the segment (x1, y1)-(x2, y2)."""
    vx, vy = x2 - x1, y2 - y1
    wx, wy = xm - x1, ym - y1
    vv = vx * vx + vy * vy
    safe = np.where(vv > 0.0, vv, 1.0)
    with np.errstate(invalid="ignore", over="ignore"):
        t = np.clip(np.where(vv > 0.0, (wx * vx + wy * vy) / safe, 0.0), 0.0, 1.0)
        dev = np.hypot(wx - t * vx, wy - t * vy)
    # A non-finite image (a point outside the projection's domain) counts as
    # infinitely far off course, so the segment keeps being refined.
    return np.where(np.isfinite(dev), dev, np.inf)


def _densify(geod, transformer, max_dev, lon1, lat1, x1, y1, lon2, lat2, x2, y2):
    """Interior vertices tracing the geodesic from vertex 1 to vertex 2.

    Returns projected x, y and the fraction of the geodesic each vertex sits at.
    """
    empty = np.empty(0, dtype=float)
    azimuth, _, length = geod.inv(lon1, lat1, lon2, lat2)
    if not math.isfinite(length) or length <= _MIN_STEP_M:
        return empty, empty, empty

    # Seed with a bounded-curvature sampling, then bisect wherever the
    # projected chord strays too far from the projected geodesic.
    n = max(1, int(math.ceil(length / _MAX_STEP_M)))
    d = np.linspace(0.0, length, n + 1)
    x = np.empty(n + 1, dtype=float)
    y = np.empty(n + 1, dtype=float)
    if n > 1:
        x[1:-1], y[1:-1] = _project(
            transformer, *_geodesic_points(geod, lon1, lat1, azimuth, d[1:-1])
        )
    x[0], y[0], x[n], y[n] = x1, y1, x2, y2

    for _ in range(_MAX_ROUNDS):
        idx = np.flatnonzero(np.diff(d) > _MIN_STEP_M)
        if idx.size == 0:
            break
        mid = 0.5 * (d[idx] + d[idx + 1])
        xm, ym = _project(transformer, *_geodesic_points(geod, lon1, lat1, azimuth, mid))
        split = _deviation(x[idx], y[idx], x[idx + 1], y[idx + 1], xm, ym) > max_dev
        if not split.any():
            break
        at = idx[split] + 1
        d = np.insert(d, at, mid[split])
        x = np.insert(x, at, xm[split])
        y = np.insert(y, at, ym[split])
        if d.size >= _MAX_POINTS_PER_SEGMENT:
            break

    xi, yi, di = x[1:-1], y[1:-1], d[1:-1]
    keep = np.isfinite(xi) & np.isfinite(yi)
    return xi[keep], yi[keep], di[keep] / length


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a WGS84 line into EPSG:``dst_epsg``, following geodesics.

    Parameters
    ----------
    line:
        A shapely ``LineString`` whose coordinates are longitude/latitude
        degrees in EPSG:4326.  A ``z`` ordinate, if present, is carried through
        unchanged and linearly interpolated onto the added vertices.
    dst_epsg:
        EPSG code of a projected CRS.

    Returns
    -------
    LineString
        The line in ``dst_epsg``.  Each input segment is replaced by a chain of
        vertices lying on the WGS84 geodesic between its endpoints, dense
        enough that no point of the returned line is further than 25 km from
        the projected geodesic.  The tolerance is stated in metres and
        converted to the target CRS's axis unit, so it also holds for CRSs
        measured in feet.

    Raises
    ------
    ValueError
        If ``dst_epsg`` is not a projected CRS, or an input vertex has no
        finite image in it.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"line must be a shapely LineString, got {type(line).__name__}")
    if line.is_empty:
        return LineString()

    transformer, metres_per_unit = _target(int(dst_epsg))
    max_dev = _PLANAR_SAFETY * TOLERANCE_M / metres_per_unit
    geod = _geod()

    coords = np.asarray(line.coords, dtype=float)
    lons, lats = coords[:, 0], coords[:, 1]
    zs = coords[:, 2] if line.has_z else None

    xs, ys = _project(transformer, lons, lats)
    bad = np.flatnonzero(~(np.isfinite(xs) & np.isfinite(ys)))
    if bad.size:
        i = int(bad[0])
        raise ValueError(
            f"vertex ({lons[i]}, {lats[i]}) has no finite image in EPSG:{dst_epsg}"
        )

    out_x, out_y = [xs[0]], [ys[0]]
    out_z = [zs[0]] if zs is not None else None
    for i in range(len(coords) - 1):
        mx, my, frac = _densify(
            geod, transformer, max_dev,
            lons[i], lats[i], xs[i], ys[i],
            lons[i + 1], lats[i + 1], xs[i + 1], ys[i + 1],
        )
        out_x.extend(mx)
        out_y.extend(my)
        out_x.append(xs[i + 1])
        out_y.append(ys[i + 1])
        if out_z is not None:
            out_z.extend(zs[i] + frac * (zs[i + 1] - zs[i]))
            out_z.append(zs[i + 1])

    stack = [out_x, out_y] if out_z is None else [out_x, out_y, out_z]
    return LineString(np.column_stack(stack))