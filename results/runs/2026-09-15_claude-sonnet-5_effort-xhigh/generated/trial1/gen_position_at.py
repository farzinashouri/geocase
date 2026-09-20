"""Estimate a ship's position at a given time via geodesic interpolation."""

import bisect

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Return the (lon, lat) position interpolated at time `t`.

    `fixes` is a chronologically sorted list of (timestamp, lon, lat)
    tuples, and `t` lies between the first and last timestamp. The
    ship is assumed to move at constant speed along the geodesic
    (shortest ellipsoidal path) between consecutive fixes, which stays
    accurate near the antimeridian, at high latitudes, and near the
    poles, unlike naive linear interpolation of lon/lat.
    """
    times = [fix[0] for fix in fixes]
    idx = bisect.bisect_left(times, t)

    if idx < len(times) and times[idx] == t:
        _, lon, lat = fixes[idx]
        return (lon, lat)

    t0, lon0, lat0 = fixes[idx - 1]
    t1, lon1, lat1 = fixes[idx]

    if t1 == t0:
        return (lon0, lat0)

    fraction = (t - t0) / (t1 - t0)

    azimuth, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = _GEOD.fwd(lon0, lat0, azimuth, distance * fraction)

    return (lon, lat)