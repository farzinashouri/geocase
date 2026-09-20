```python
"""Estimate a ship's position at a given time from a sorted list of GPS fixes.

Interpolation is done along the geodesic between the two bracketing fixes
(WGS84 ellipsoid via pyproj), so results are correct near the poles, across
the antimeridian, and over long gaps where straight lon/lat interpolation
would drift off the great-circle track.
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
    """Return the estimated (lon, lat) of the ship at Unix time ``t``.

    ``fixes`` must be sorted by timestamp and contain at least one fix.
    ``t`` must lie within [first timestamp, last timestamp].
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    t0, tn = fixes[0][0], fixes[-1][0]
    if t < t0 or t > tn:
        raise ValueError(f"t={t} is outside the fix range [{t0}, {tn}]")

    timestamps = [f[0] for f in fixes]
    # Index of the first fix strictly after t.
    idx = bisect_right(timestamps, t)

    # Exact hit on a fix (idx points past it), or t equals the last fix.
    if idx > 0 and timestamps[idx - 1] == t:
        _, lon, lat = fixes[idx - 1]
        return (_normalize_lon(lon), lat)

    # idx >= 1 is guaranteed here since t >= t0 and t != any fix timestamp
    # means t > t0, so bisect_right returns at least 1.
    ta, lon_a, lat_a = fixes[idx - 1]
    tb, lon_b, lat_b = fixes[idx]

    if tb == ta:
        return (_normalize_lon(lon_a), lat_a)

    frac = (t - ta) / (tb - ta)

    # Geodesic from A to B: forward azimuth and distance on the ellipsoid.
    az_ab, _az_ba, dist = _GEOD.inv(lon_a, lat_a, lon_b, lat_b)
    if dist == 0.0:
        return (_normalize_lon(lon_a), lat_a)

    lon, lat, _ = _GEOD.fwd(lon_a, lat_a, az_ab, dist * frac)
    return (_normalize_lon(lon), lat)
```