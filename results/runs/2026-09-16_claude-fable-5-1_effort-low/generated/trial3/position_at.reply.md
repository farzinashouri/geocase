Writing the module now: a great-circle (geodesic) interpolation between the bracketing fixes using pyproj, which handles antimeridian and polar cases correctly.

```python
"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

Positions are interpolated along the geodesic between the two fixes that
bracket the requested time, so results are correct across the antimeridian
and near the poles.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import Sequence, Tuple

from pyproj import Geod

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)

_GEOD = Geod(ellps="WGS84")


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180]."""
    lon = (lon + 180.0) % 360.0 - 180.0
    return lon


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated (lon, lat) of the ship at time ``t``.

    ``fixes`` must be a non-empty list of ``(timestamp, lon, lat)`` tuples
    sorted by timestamp, and ``t`` must lie within
    ``[fixes[0][0], fixes[-1][0]]``.
    """
    if not fixes:
        raise ValueError("fixes must be non-empty")
    t0, tn = fixes[0][0], fixes[-1][0]
    if not (t0 <= t <= tn):
        raise ValueError(f"t={t} is outside the fix range [{t0}, {tn}]")

    times = [f[0] for f in fixes]
    idx = bisect_right(times, t)

    # Exact hit on a fix (or duplicate timestamps): return that fix.
    if idx > 0 and times[idx - 1] == t:
        _, lon, lat = fixes[idx - 1]
        return (_normalize_lon(lon), lat)

    ta, lon_a, lat_a = fixes[idx - 1]
    tb, lon_b, lat_b = fixes[idx]

    if tb == ta:
        return (_normalize_lon(lon_a), lat_a)

    frac = (t - ta) / (tb - ta)

    az, _, dist = _GEOD.inv(lon_a, lat_a, lon_b, lat_b)
    if dist == 0.0:
        return (_normalize_lon(lon_a), lat_a)

    lon, lat, _ = _GEOD.fwd(lon_a, lat_a, az, dist * frac)
    return (_normalize_lon(lon), lat)
```