"""Interpolate a ship's position between GPS fixes using geodesic interpolation."""

from bisect import bisect_left

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Estimate a ship's (lon, lat) position at time t from sorted GPS fixes.

    fixes: chronologically sorted list of (timestamp, lon, lat) tuples.
    t: Unix timestamp between fixes[0][0] and fixes[-1][0] (inclusive).

    Interpolation follows the WGS84 geodesic (great-circle-on-the-ellipsoid)
    path between the two bracketing fixes, parameterized by elapsed time,
    which stays accurate near the antimeridian and at high latitudes where
    naive linear interpolation of longitude/latitude would not.
    """
    if not fixes:
        raise ValueError("fixes must be a non-empty list")

    timestamps = [f[0] for f in fixes]
    i = bisect_left(timestamps, t)

    if i < len(fixes) and timestamps[i] == t:
        _, lon, lat = fixes[i]
        return (lon, lat)

    if i == 0 or i == len(fixes):
        raise ValueError("t must be between the first and last fix")

    t0, lon0, lat0 = fixes[i - 1]
    t1, lon1, lat1 = fixes[i]

    fraction = (t - t0) / (t1 - t0)

    forward_azimuth, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = _GEOD.fwd(lon0, lat0, forward_azimuth, distance * fraction)

    return (lon, lat)