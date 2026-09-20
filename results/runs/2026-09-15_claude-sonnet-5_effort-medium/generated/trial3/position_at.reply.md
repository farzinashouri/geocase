```python
"""Interpolate a ship's position at an arbitrary time from a sorted list of GPS fixes."""

import bisect

from pyproj import Geod

_geod = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Estimate (lon, lat) at time t via geodesic interpolation between bracketing fixes.

    fixes: chronologically sorted list of (timestamp, lon, lat).
    t: timestamp with fixes[0][0] <= t <= fixes[-1][0].
    """
    timestamps = [f[0] for f in fixes]
    idx = bisect.bisect_left(timestamps, t)

    if idx < len(fixes) and timestamps[idx] == t:
        _, lon, lat = fixes[idx]
        return (lon, lat)

    i0 = idx - 1
    i1 = idx
    t0, lon0, lat0 = fixes[i0]
    t1, lon1, lat1 = fixes[i1]

    if t1 == t0:
        return (lon0, lat0)

    frac = (t - t0) / (t1 - t0)

    az12, _, dist = _geod.inv(lon0, lat0, lon1, lat1)
    if dist == 0:
        return (lon0, lat0)

    lon, lat, _ = _geod.fwd(lon0, lat0, az12, dist * frac)
    return (lon, lat)
```