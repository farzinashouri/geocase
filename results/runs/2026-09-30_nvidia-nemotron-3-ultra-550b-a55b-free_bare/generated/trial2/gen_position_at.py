"""
Module for interpolating a ship's position at a given timestamp from a series of GPS fixes.
"""

import bisect
from pyproj import Geod


def position_at(fixes, t):
    """
    Estimate the ship's position at time `t` by geodesic interpolation between GPS fixes.

    Parameters
    ----------
    fixes : list of tuple (float, float, float)
        Chronologically sorted list of (timestamp, longitude, latitude) GPS fixes.
        Timestamps are Unix seconds; coordinates are WGS84 (longitude, latitude).
    t : float
        Target timestamp (Unix seconds) between the first and last fix (inclusive).

    Returns
    -------
    tuple (float, float)
        Estimated (longitude, latitude) at time `t`.

    Raises
    ------
    ValueError
        If `fixes` is empty or `t` is outside the range of the provided fixes.
    """
    if not fixes:
        raise ValueError("fixes list is empty")

    timestamps = [fix[0] for fix in fixes]
    i = bisect.bisect_left(timestamps, t)

    # Exact match to a fix
    if i < len(fixes) and timestamps[i] == t:
        return (fixes[i][1], fixes[i][2])

    # t is before the first fix or after the last fix
    if i == 0:
        raise ValueError("t is before the first fix")
    if i == len(fixes):
        raise ValueError("t is after the last fix")

    # Interpolate between fixes[i-1] and fixes[i]
    t0, lon0, lat0 = fixes[i - 1]
    t1, lon1, lat1 = fixes[i]

    frac = (t - t0) / (t1 - t0)

    geod = Geod(ellps="WGS84")
    az12, _, dist = geod.inv(lon0, lat0, lon1, lat1)
    lon, lat, _ = geod.fwd(lon0, lat0, az12, frac * dist)

    return (lon, lat)