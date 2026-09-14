from pyproj import Geod


def position_at(fixes, t):
    """
    Estimate ship position at time t using great circle interpolation.

    Args:
        fixes: List of (timestamp, lon, lat) tuples, chronologically sorted
        t: Target timestamp (between first and last fix)

    Returns:
        (lon, lat) tuple of estimated position at time t
    """
    # Find the two fixes that bracket time t
    for i in range(len(fixes) - 1):
        if fixes[i][0] <= t <= fixes[i + 1][0]:
            t1, lon1, lat1 = fixes[i]
            t2, lon2, lat2 = fixes[i + 1]
            break
    else:
        raise ValueError("Time t is outside the range of fixes")

    # Handle case where the two fixes have the same timestamp
    if t1 == t2:
        return (lon1, lat1)

    # Use WGS84 geodetic calculations for great circle interpolation
    geod = Geod(ellps='WGS84')

    # Get great circle distance and forward azimuth between fixes
    az12, az21, distance = geod.inv(lon1, lat1, lon2, lat2)

    # Interpolate: calculate fraction of time between the two fixes
    frac = (t - t1) / (t2 - t1)

    # Calculate position at time t along the great circle path
    lon_out, lat_out, _ = geod.fwd(lon1, lat1, az12, distance * frac)

    return (lon_out, lat_out)