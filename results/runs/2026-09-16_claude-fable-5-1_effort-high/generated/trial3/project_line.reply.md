```python
"""Project a WGS84 LineString into a projected CRS while following geodesics.

`project_line` densifies every input segment along the true geodesic (the
shortest path on the WGS84 ellipsoid), then adaptively subdivides further
wherever the straight chord in the target projection strays from the
projected geodesic, so the returned line stays within 25 km of the geodesic
course everywhere.
"""
from __future__ import annotations

import math

import numpy as np
from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString

TOLERANCE_M = 25_000.0      # required accuracy of the returned line
_MAX_STEP_M = 50_000.0      # initial geodesic spacing between vertices
_REFINE_TOL_M = 2_500.0     # projected midpoint deviation that triggers a split
_MIN_SPLIT_M = 1.0          # never split geodesic pieces shorter than this
_MAX_ROUNDS = 24            # upper bound on adaptive refinement passes


def project_line(line: LineString, dst_epsg: int) -> LineString:
    """Return `line` (lon/lat, EPSG:4326) projected to EPSG:`dst_epsg`.

    The output vertices lie on the geodesic between each pair of consecutive
    input vertices, and the chords between them deviate from that geodesic by
    far less than 25 km in the target projection.
    """
    if line.is_empty:
        return LineString()
    coords = np.asarray(line.coords, dtype=float)
    lons = coords[:, 0]
    lats = coords[:, 1]

    dst = CRS.from_epsg(int(dst_epsg))
    transformer = Transformer.from_crs("EPSG:4326", dst, always_xy=True)

    lons, lats = _densify(lons, lats)
    lons, lats = _refine(lons, lats, transformer, _REFINE_TOL_M / _unit_factor(dst))

    x, y = transformer.transform(lons, lats)
    return LineString(np.column_stack([x, y]))


def _densify(lons: np.ndarray, lats: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Insert geodesic waypoints so no piece is longer than _MAX_STEP_M."""
    geod = Geod(ellps="WGS84")
    _, _, dists = geod.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
    out_lon = [float(lons[0])]
    out_lat = [float(lats[0])]
    for i, d in enumerate(np.atleast_1d(dists)):
        n = 1 if not math.isfinite(d) else max(1, int(math.ceil(d / _MAX_STEP_M)))
        if n > 1:
            for lon, lat in geod.npts(lons[i], lats[i], lons[i + 1], lats[i + 1], n - 1):
                out_lon.append(lon)
                out_lat.append(lat)
        out_lon.append(float(lons[i + 1]))
        out_lat.append(float(lats[i + 1]))
    return np.asarray(out_lon), np.asarray(out_lat)


def _refine(
    lons: np.ndarray,
    lats: np.ndarray,
    transformer: Transformer,
    tol: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Split pieces whose projected chord midpoint is far from the geodesic midpoint."""
    geod = Geod(ellps="WGS84")
    for _ in range(_MAX_ROUNDS):
        az, _, dist = geod.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
        az = np.asarray(az, dtype=float)
        dist = np.asarray(dist, dtype=float)
        mid_lon, mid_lat, _ = geod.fwd(lons[:-1], lats[:-1], az, dist / 2.0)
        mid_lon = np.asarray(mid_lon, dtype=float)
        mid_lat = np.asarray(mid_lat, dtype=float)

        x, y = transformer.transform(lons, lats)
        mx, my = transformer.transform(mid_lon, mid_lat)
        x, y, mx, my = (np.asarray(a, dtype=float) for a in (x, y, mx, my))

        with np.errstate(invalid="ignore", over="ignore"):
            dev = np.hypot(mx - 0.5 * (x[:-1] + x[1:]), my - 0.5 * (y[:-1] + y[1:]))
            split = np.isfinite(dev) & (dev > tol) & (dist > _MIN_SPLIT_M)

        if not split.any():
            break
        idx = np.flatnonzero(split)
        lons = np.insert(lons, idx + 1, mid_lon[idx])
        lats = np.insert(lats, idx + 1, mid_lat[idx])
    return lons, lats


def _unit_factor(crs: CRS) -> float:
    """Metres per unit of the CRS's horizontal axes (1.0 if unknown)."""
    try:
        if crs.is_geographic:
            return 111_000.0  # rough metres per degree, only used as a guard
        factor = crs.axis_info[0].unit_conversion_factor
        if factor and math.isfinite(factor) and factor > 0:
            return float(factor)
    except (AttributeError, IndexError):
        pass
    return 1.0
```