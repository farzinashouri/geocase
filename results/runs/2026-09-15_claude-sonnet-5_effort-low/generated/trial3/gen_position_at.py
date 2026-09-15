"""Estimate a ship's position at time t via great-circle interpolation between bracketing GPS fixes."""

import bisect

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    if not fixes:
        raise ValueError("fixes must be non-empty")

    times = [f[0] for f in fixes]
    if t < times[0] or t > times[-1]:
        raise ValueError("t must be between the first and last fix")

    idx = bisect.bisect_left(times, t)
    if times[idx] == t:
        _, lon, lat = fixes[idx]
        return (lon, lat)

    t0, lon0, lat0 = fixes[idx - 1]
    t1, lon1, lat1 = fixes[idx]

    if t1 == t0:
        return (lon0, lat0)

    frac = (t - t0) / (t1 - t0)

    az12, _, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = _GEOD.fwd(lon0, lat0, az12, dist * frac)

    return (lon, lat)