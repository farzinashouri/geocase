```python
"""Project a WGS84 (EPSG:4326) LineString into a projected CRS along geodesics.

``project_line(line, dst_epsg)`` returns a shapely ``LineString`` in the target
CRS that follows the WGS84 geodesic (shortest path on the ellipsoid) between
each pair of consecutive input vertices.  Vertices are inserted along every
geodesic adaptively until the projected polyline stays well inside the
requested tolerance (25 km by default) of the true geodesic.  The deviation is
checked both in the projected plane (converted to metres via the CRS's linear
unit) and on the ellipsoid (geodesic distance), so the result is accurate under
either interpretation of "within 25 km".

Notes
-----
* Input coordinates are interpreted as (longitude, latitude); output
  coordinates are (easting, northing) regardless of the CRS's declared axis
  order (``always_xy=True``).  Z/M values are dropped.
* Every input vertex is preserved exactly (projected) in the output.
* If a geodesic crosses a discontinuity of the target projection (for example
  the antimeridian in Web Mercator) the output contains a straight jump across
  the map at that point; a single LineString cannot represent that break.
"""

from __future__ import annotations

import numpy as np
import shapely
from pyproj import CRS, Geod, Transformer
from pyproj.enums import TransformDirection
from shapely.geometry import LineString

__all__ = ["project_line"]

_DEFAULT_TOLERANCE_M = 25_000.0
# Refinement targets this fraction of the tolerance so the sampled deviation
# checks below leave a comfortable margin (1 km for the default tolerance).
_SAFETY_FACTOR = 25.0
# Initial vertex spacing along each geodesic (on the ellipsoid) before the
# adaptive refinement starts.
_INITIAL_SPACING_M = 100_000.0
# Pieces shorter than this on the ellipsoid are never subdivided further
# (guards against unrepresentable projection discontinuities).
_MIN_PIECE_M = 10.0
_MAX_ROUNDS = 64
# Fractions along each piece at which the deviation is measured.  Several
# interior points are used so symmetric S-shaped deviations (e.g. a great
# circle crossing the equator in Mercator) cannot hide from a midpoint test.
_CHECK_FRACTIONS = (1 / 6, 1 / 3, 1 / 2, 2 / 3, 5 / 6)


def project_line(line, dst_epsg, tolerance_m=_DEFAULT_TOLERANCE_M):
    """Project a lon/lat LineString to ``dst_epsg`` following geodesics.

    Parameters
    ----------
    line : shapely.geometry.LineString
        Vertices are (longitude, latitude) degrees in EPSG:4326.
    dst_epsg : int
        EPSG code of a projected CRS (any ``pyproj.CRS.from_user_input``
        value is accepted as well).
    tolerance_m : float, optional
        Maximum allowed deviation, in metres, between the returned polyline
        and the true geodesic.  Defaults to 25 km.

    Returns
    -------
    shapely.geometry.LineString
        A 2-D LineString in the target CRS with (easting, northing) vertices.
    """
    if not isinstance(line, LineString):
        raise TypeError("line must be a shapely LineString")
    if line.is_empty:
        return LineString()
    coords = np.asarray(shapely.get_coordinates(line), dtype=float)
    if coords.shape[0] < 2:
        raise ValueError("line must have at least two vertices")
    if not np.all(np.isfinite(coords)) or np.any(np.abs(coords[:, 1]) > 90.0):
        raise ValueError("line coordinates must be finite longitude/latitude degrees")
    if not tolerance_m > 0:
        raise ValueError("tolerance_m must be positive")

    dst_crs = CRS.from_user_input(dst_epsg)
    transformer = Transformer.from_crs(CRS.from_epsg(4326), dst_crs, always_xy=True)
    meters_per_unit = _meters_per_unit(dst_crs)
    geod = Geod(ellps="WGS84")
    target = float(tolerance_m) / _SAFETY_FACTOR

    # Geodesic parameters of every input segment.
    lon0, lat0 = coords[:-1, 0], coords[:-1, 1]
    lon1, lat1 = coords[1:, 0], coords[1:, 1]
    az, _, dist = geod.inv(lon0, lat0, lon1, lat1)
    az = np.asarray(az, dtype=float)
    dist = np.asarray(dist, dtype=float)

    def geo_points(s, tt):
        """Lon/lat of the point at fraction ``tt`` along input segment ``s``."""
        if s.size == 0:
            return np.empty(0), np.empty(0)
        lon, lat, _ = geod.fwd(lon0[s], lat0[s], az[s], tt * dist[s])
        lon = np.array(lon, dtype=float)
        lat = np.array(lat, dtype=float)
        m = tt <= 0.0
        lon[m], lat[m] = lon0[s[m]], lat0[s[m]]
        m = tt >= 1.0
        lon[m], lat[m] = lon1[s[m]], lat1[s[m]]
        return lon, lat

    def project(lon, lat):
        with np.errstate(all="ignore"):
            x, y = transformer.transform(lon, lat)
        return np.asarray(x, dtype=float), np.asarray(y, dtype=float)

    def unproject(x, y):
        with np.errstate(all="ignore"):
            lon, lat = transformer.transform(x, y, direction=TransformDirection.INVERSE)
        return np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)

    # Node list, sorted by (segment index, fraction along the segment).  Each
    # segment carries its own t=0 and t=1 nodes; the duplicate at segment
    # boundaries is dropped at the end.
    nseg = dist.size
    npieces = np.maximum(1, np.ceil(dist / _INITIAL_SPACING_M)).astype(np.int64)
    counts = npieces + 1
    seg = np.repeat(np.arange(nseg), counts)
    first = np.repeat(np.cumsum(counts) - counts, counts)
    t = (np.arange(seg.size) - first) / np.repeat(npieces, counts)
    x, y = project(*geo_points(seg, t))
    check = np.ones(seg.size - 1, dtype=bool)

    for _ in range(_MAX_ROUNDS):
        j = np.flatnonzero(check & (seg[:-1] == seg[1:]))
        if j.size == 0:
            break
        s = seg[j]
        t0, t1 = t[j], t[j + 1]
        long_enough = (t1 - t0) * dist[s] > _MIN_PIECE_M
        j, s, t0, t1 = j[long_enough], s[long_enough], t0[long_enough], t1[long_enough]
        if j.size == 0:
            break
        x0, y0, x1, y1 = x[j], y[j], x[j + 1], y[j + 1]
        bad = np.zeros(j.size, dtype=bool)

        for f in _CHECK_FRACTIONS:
            glon, glat = geo_points(s, t0 + f * (t1 - t0))
            gx, gy = project(glon, glat)

            # Deviation measured in the projected plane.
            if meters_per_unit is not None:
                dev = _point_segment_distance(gx, gy, x0, y0, x1, y1) * meters_per_unit
                bad |= np.isfinite(dev) & (dev > target)

            # Deviation measured on the ellipsoid: a point of the output chord,
            # taken back to lon/lat, versus the corresponding geodesic point.
            with np.errstate(all="ignore"):
                cx = x0 + f * (x1 - x0)
                cy = y0 + f * (y1 - y0)
            clon, clat = unproject(cx, cy)
            ok = np.isfinite(clon) & np.isfinite(clat) & np.isfinite(glon) & np.isfinite(glat)
            if ok.any():
                _, _, dg = geod.inv(
                    clon[ok], np.clip(clat[ok], -90.0, 90.0), glon[ok], glat[ok]
                )
                dg = np.asarray(dg, dtype=float)
                bad[np.flatnonzero(ok)[np.isfinite(dg) & (dg > target)]] = True

        jb = j[bad]
        if jb.size == 0:
            break

        # Split every offending piece at its geodesic midpoint.
        ns = seg[jb]
        nt = 0.5 * (t[jb] + t[jb + 1])
        nx, ny = project(*geo_points(ns, nt))
        pos = jb + 1
        seg = np.insert(seg, pos, ns)
        t = np.insert(t, pos, nt)
        x = np.insert(x, pos, nx)
        y = np.insert(y, pos, ny)
        new_idx = pos + np.arange(pos.size)
        check = np.zeros(seg.size - 1, dtype=bool)
        check[new_idx - 1] = True
        check[new_idx] = True

    keep = ~((seg > 0) & (t <= 0.0))
    return LineString(np.column_stack([x[keep], y[keep]]))


def _meters_per_unit(crs):
    """Metres per linear unit of a projected CRS, or None if not projected."""
    if not crs.is_projected:
        return None
    for axis in crs.axis_info:
        factor = getattr(axis, "unit_conversion_factor", None)
        if factor and np.isfinite(factor) and factor > 0:
            return float(factor)
    return 1.0


def _point_segment_distance(px, py, ax, ay, bx, by):
    """Vectorised Euclidean distance from points P to segments A-B."""
    with np.errstate(all="ignore"):
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        u = ((px - ax) * dx + (py - ay) * dy) / np.where(l2 > 0.0, l2, 1.0)
        u = np.clip(np.where(l2 > 0.0, u, 0.0), 0.0, 1.0)
        return np.hypot(px - (ax + u * dx), py - (ay + u * dy))
```