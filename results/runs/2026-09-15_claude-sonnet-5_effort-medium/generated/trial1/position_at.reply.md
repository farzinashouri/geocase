```python
"""Interpolate a ship's position along a geodesic between two known GPS fixes."""

import bisect

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Estimate (lon, lat) at time t from a sorted list of (timestamp, lon, lat) fixes.

    Uses geodesic (great-circle, ellipsoidal) interpolation along the shortest
    path between the two bracketing fixes, parameterized linearly by time,
    so results stay accurate anywhere on the globe (including near poles or
    across the antimeridian).
    """
    times = [f[0] for f in fixes]
    idx = bisect.bisect_right(times, t) - 1
    idx = max(0, min(idx, len(fixes) - 2))

    t0, lon0, lat0 = fixes[idx]
    t1, lon1, lat1 = fixes[idx + 1]

    if t1 == t0:
        return (lon0, lat0)

    frac = (t - t0) / (t1 - t0)
    frac = max(0.0, min(1.0, frac))

    if lon0 == lon1 and lat0 == lat1:
        return (lon0, lat0)

    az12, _, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = _GEOD.fwd(lon0, lat0, az12, dist * frac)

    return (lon, lat)
```