"""Interpolate a ship's position along a track of GPS fixes."""

import bisect

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Estimate a ship's (lon, lat) position at time t.

    fixes is a chronologically sorted list of (timestamp, lon, lat) tuples
    with timestamp in Unix seconds. t must lie between the first and last
    fix's timestamps. The position is found by interpolating along the
    geodesic (great-circle, WGS84) path between the two fixes bracketing
    t, assuming constant speed along that path. This stays accurate near
    the antimeridian and poles, unlike naive linear interpolation on
    longitude/latitude.
    """
    timestamps = [fix[0] for fix in fixes]
    idx = bisect.bisect_left(timestamps, t)

    if idx < len(timestamps) and timestamps[idx] == t:
        _, lon, lat = fixes[idx]
        return (lon, lat)

    t0, lon0, lat0 = fixes[idx - 1]
    t1, lon1, lat1 = fixes[idx]

    if t1 == t0:
        return (lon0, lat0)

    fraction = (t - t0) / (t1 - t0)

    az_forward, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = _GEOD.fwd(lon0, lat0, az_forward, distance * fraction)
    return (lon, lat)