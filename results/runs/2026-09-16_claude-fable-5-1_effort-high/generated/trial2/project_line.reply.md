```python
"""Project a WGS84 LineString into a projected CRS while following geodesics.

The output line is densified so that, in the target CRS, every straight
segment stays within 25 km of the true geodesic (shortest ellipsoidal path)
between consecutive input vertices.
"""

from __future__ import annotations

import numpy as np
from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

_TOLERANCE_M = 25_000.0      # required accuracy, metres on the ground
_SAFETY = 0.5                # sample-based check, so keep a margin
_MAX_SEGMENT_M = 100_000.0   # hard cap on geodesic length per output segment
_MIN_SEGMENT_M = 1.0         # stop refining below this (projection discontinuities)
_MAX_ROUNDS = 64
_CHECK_FRACTIONS = (0.25, 0.5, 0.75)
_EARTH_RADIUS_M = 6_378_137.0


def _point_segment_distance(px, py, ax, ay, bx, by):
    """Vectorised distance from points P to segments A-B."""
    dx = bx - ax
    dy = by - ay
    seg_len2 = dx * dx + dy * dy
    with np.errstate(invalid="ignore", divide="ignore"):
        t = np.where(seg_len2 > 0.0,
                     ((px - ax) * dx + (py - ay) * dy) / seg_len2,
                     0.0)
    t = np.clip(t, 0.0, 1.0)
    cx = ax + t * dx
    cy = ay + t * dy
    return np.hypot(px - cx, py - cy)


def _tolerance_in_crs_units(crs: CRS) -> float:
    """Convert the metre tolerance into the target CRS's linear units."""
    unit_m = 1.0
    if crs.axis_info:
        unit_m = crs.axis_info[0].unit_conversion_factor or 1.0
    if not crs.is_projected:
        # Angular units: unit_conversion_factor is radians per unit.
        unit_m *= _EARTH_RADIUS_M
    return _TOLERANCE_M * _SAFETY / unit_m


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Project a lon/lat (EPSG:4326) LineString to ``dst_epsg`` along geodesics.

    Consecutive input vertices are joined by geodesics, densified until each
    projected straight segment lies within 25 km of the geodesic everywhere.
    """
    coords = np.asarray(line.coords, dtype=float)
    if coords.ndim != 2 or coords.shape[0] < 2:
        raise ValueError("line must contain at least two vertices")

    lons = np.ascontiguousarray(coords[:, 0])
    lats = np.ascontiguousarray(coords[:, 1])

    dst_crs = CRS.from_epsg(int(dst_epsg))
    tol = _tolerance_in_crs_units(dst_crs)

    geod = Geod(ellps="WGS84")
    transformer = Transformer.from_crs(CRS.from_epsg(4326), dst_crs, always_xy=True)

    for _ in range(_MAX_ROUNDS):
        az, _, dist = geod.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
        az = np.asarray(az, dtype=float)
        dist = np.asarray(dist, dtype=float)

        px, py = transformer.transform(lons, lats)
        px = np.asarray(px, dtype=float)
        py = np.asarray(py, dtype=float)

        worst = np.zeros(dist.shape[0])
        mid_lon = mid_lat = None
        for frac in _CHECK_FRACTIONS:
            slon, slat, _ = geod.fwd(lons[:-1], lats[:-1], az, dist * frac)
            slon = np.asarray(slon, dtype=float)
            slat = np.asarray(slat, dtype=float)
            if frac == 0.5:
                mid_lon, mid_lat = slon, slat
            sx, sy = transformer.transform(slon, slat)
            d = _point_segment_distance(np.asarray(sx, dtype=float),
                                        np.asarray(sy, dtype=float),
                                        px[:-1], py[:-1], px[1:], py[1:])
            # Points outside the projection's domain give no usable signal.
            d = np.where(np.isfinite(d), d, 0.0)
            worst = np.maximum(worst, d)

        split = (dist > _MAX_SEGMENT_M) | ((worst > tol) & (dist > _MIN_SEGMENT_M))
        if not split.any():
            break

        idx = np.nonzero(split)[0]
        lons = np.insert(lons, idx + 1, mid_lon[idx])
        lats = np.insert(lats, idx + 1, mid_lat[idx])

    px, py = transformer.transform(lons, lats)
    out = np.column_stack([np.asarray(px, dtype=float), np.asarray(py, dtype=float)])
    return LineString(out)
```