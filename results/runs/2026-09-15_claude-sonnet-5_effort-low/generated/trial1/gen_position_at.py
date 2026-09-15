"""Interpolate a ship's position along its GPS track using great-circle geometry."""

from bisect import bisect_left

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Estimate (lon, lat) at time t via geodesic interpolation between bracketing fixes.

    fixes: chronologically sorted list of (timestamp, lon, lat).
    t: unix timestamp with fixes[0][0] <= t <= fixes[-1][0].
    """
    timestamps = [f[0] for f in fixes]

    if t <= timestamps[0]:
        return (fixes[0][1], fixes[0][2])
    if t >= timestamps[-1]:
        return (fixes[-1][1], fixes[-1][2])

    idx = bisect_left(timestamps, t)
    if timestamps[idx] == t:
        return (fixes[idx][1], fixes[idx][2])

    t0, lon0, lat0 = fixes[idx - 1]
    t1, lon1, lat1 = fixes[idx]

    if t1 == t0:
        return (lon0, lat0)

    fraction = (t - t0) / (t1 - t0)

    if lon0 == lon1 and lat0 == lat1:
        return (lon0, lat0)

    az12, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = _GEOD.fwd(lon0, lat0, az12, distance * fraction)

    return (lon, lat)