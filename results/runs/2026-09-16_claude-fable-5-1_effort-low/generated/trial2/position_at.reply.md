```python
"""Estimate a ship's position at a given time from a sorted list of GPS fixes.

Interpolation is performed along the geodesic between the two fixes that
bracket the requested time, using pyproj's WGS84 geodesic routines. This
gives correct results anywhere on the ocean, including across the antimeridian
and near the poles, where naive linear interpolation of lon/lat would fail.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import Sequence, Tuple

from pyproj import Geod

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)

_GEOD = Geod(ellps="WGS84")


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into the range [-180, 180]."""
    lon = (lon + 180.0) % 360.0 - 180.0
    return lon


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated (lon, lat) of the ship at Unix time ``t``.

    ``fixes`` must be a non-empty, chronologically sorted sequence of
    ``(timestamp, lon, lat)`` tuples in WGS84. ``t`` must lie within
    ``[fixes[0][0], fixes[-1][0]]``.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    t0 = fixes[0][0]
    t1 = fixes[-1][0]
    if t < t0 or t > t1:
        raise ValueError(f"t={t} is outside the fix range [{t0}, {t1}]")

    # Exact match on the endpoints, or a single fix, needs no interpolation.
    if t == t0:
        return (_normalize_lon(fixes[0][1]), fixes[0][2])
    if t == t1:
        return (_normalize_lon(fixes[-1][1]), fixes[-1][2])

    timestamps = [f[0] for f in fixes]
    # Index of the last fix with timestamp <= t.
    i = bisect_right(timestamps, t) - 1
    ts_a, lon_a, lat_a = fixes[i]
    ts_b, lon_b, lat_b = fixes[i + 1]

    if ts_a == t:
        return (_normalize_lon(lon_a), lat_a)

    span = ts_b - ts_a
    if span <= 0:
        # Duplicate timestamps; fall back to the earlier fix.
        return (_normalize_lon(lon_a), lat_a)

    frac = (t - ts_a) / span

    # Geodesic from A to B: forward azimuth and distance along the ellipsoid.
    fwd_az, _back_az, dist = _GEOD.inv(lon_a, lat_a, lon_b, lat_b)
    if dist == 0.0:
        return (_normalize_lon(lon_a), lat_a)

    lon, lat, _ = _GEOD.fwd(lon_a, lat_a, fwd_az, dist * frac)
    return (_normalize_lon(lon), lat)
```