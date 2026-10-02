"""
Module for interpolating a ship's position at a given timestamp from a series of GPS fixes.

The interpolation follows great-circle (geodesic) paths on the WGS84 ellipsoid,
assuming constant speed between consecutive fixes.
"""

from pyproj import Geod

# Pre-instantiated geodetic calculator for WGS84
_geod = Geod(ellps="WGS84")


def position_at(fixes, t):
    """
    Estimate the ship's position at time `t` by interpolating along geodesics.

    Parameters
    ----------
    fixes : list of tuple (timestamp, lon, lat)
        Chronologically sorted GPS fixes. Timestamps are Unix seconds (int or float).
        Longitudes and latitudes are in decimal degrees (WGS84).
    t : float or int
        Target timestamp. Must lie within the time range covered by `fixes`.

    Returns
    -------
    tuple (lon, lat)
        Interpolated longitude and latitude in decimal degrees.

    Raises
    ------
    ValueError
        If `fixes` is empty, has only one fix but `t` does not match it,
        or `t` is outside the range of the provided fixes.
    """
    if not fixes:
        raise ValueError("fixes list is empty")

    n = len(fixes)

    # If there's only one fix, we can only return it if t matches exactly.
    if n == 1:
        if t == fixes[0][0]:
            return (fixes[0][1], fixes[0][2])
        raise ValueError("t is outside the range of fixes")

    # Quick check for exact timestamp matches (handles floating-point equality).
    for fix in fixes:
        if fix[0] == t:
            return (fix[1], fix[2])

    # Find the interval [i, i+1] that brackets t.
    # Since fixes are sorted, a linear scan is sufficient for typical track lengths.
    for i in range(n - 1):
        t1, lon1, lat1 = fixes[i]
        t2, lon2, lat2 = fixes[i + 1]
        if t1 <= t <= t2:
            break
    else:
        raise ValueError("t is outside the range of fixes")

    # If the two fixes have the same timestamp, return the first one.
    if t2 == t1:
        return (lon1, lat1)

    # Time fraction between the two fixes.
    frac = (t - t1) / (t2 - t1)

    # Clamp fraction to [0, 1] to guard against tiny floating-point excursions.
    if frac <= 0.0:
        return (lon1, lat1)
    if frac >= 1.0:
        return (lon2, lat2)

    # Solve the inverse geodesic problem to get azimuth and distance.
    az12, _, dist = _geod.inv(lon1, lat1, lon2, lat2)

    # Distance to travel from the first fix at the given time fraction.
    dist_frac = frac * dist

    # Solve the forward geodesic problem to get the interpolated position.
    lon_interp, lat_interp, _ = _geod.fwd(lon1, lat1, az12, dist_frac)

    return (lon_interp, lat_interp)