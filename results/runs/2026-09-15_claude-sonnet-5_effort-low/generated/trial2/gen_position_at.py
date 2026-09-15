"""Interpolate a ship's position along a track of GPS fixes."""

import bisect

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Estimate (lon, lat) at time t by geodesic interpolation between bracketing fixes.

    fixes: chronologically sorted list of (timestamp, lon, lat).
    t: unix timestamp with fixes[0][0] <= t <= fixes[-1][0].
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

    if frac == 0.0:
        return (lon0, lat0)
    if frac == 1.0:
        return (lon1, lat1)

    az12, _, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = _GEOD.fwd(lon0, lat0, az12, dist * frac)
    return (lon, lat)