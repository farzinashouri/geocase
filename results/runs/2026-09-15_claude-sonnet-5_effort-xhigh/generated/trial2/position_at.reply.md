```python
"""Interpolate a ship's position from a sequence of GPS fixes."""

import bisect

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Estimate the ship's (lon, lat) position at time t.

    fixes: chronologically sorted list of (timestamp, lon, lat) tuples
    (Unix seconds, WGS84 degrees). t: a Unix timestamp assumed to lie
    between fixes[0][0] and fixes[-1][0].

    Interpolation is done along the geodesic (great-circle-on-ellipsoid)
    path between the two bracketing fixes, proportional to elapsed time,
    so results stay accurate near the antimeridian, at high latitudes,
    and over long inter-fix distances.
    """
    timestamps = [f[0] for f in fixes]

    if t <= timestamps[0]:
        return (fixes[0][1], fixes[0][2])
    if t >= timestamps[-1]:
        return (fixes[-1][1], fixes[-1][2])

    i = bisect.bisect_right(timestamps, t) - 1
    t0, lon0, lat0 = fixes[i]
    t1, lon1, lat1 = fixes[i + 1]

    if t1 == t0:
        return (lon0, lat0)

    frac = (t - t0) / (t1 - t0)

    az12, _, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
    if dist == 0:
        return (lon0, lat0)

    lon, lat, _ = _GEOD.fwd(lon0, lat0, az12, dist * frac)
    return (lon, lat)
```