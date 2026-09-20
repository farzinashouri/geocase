from pyproj import Geod


def position_at(fixes, t):
    """Estimate ship position at time t using geodesic interpolation."""
    # Find bracketing fixes
    for i in range(len(fixes) - 1):
        if fixes[i][0] <= t <= fixes[i + 1][0]:
            t0, lon0, lat0 = fixes[i]
            t1, lon1, lat1 = fixes[i + 1]
            break
    else:
        raise ValueError("Timestamp t is outside the range of fixes")
    
    # Handle edge case where times are equal
    if t0 == t1:
        return (lon0, lat0)
    
    # Time fraction for interpolation
    alpha = (t - t0) / (t1 - t0)
    
    # Use Geod for geodesic interpolation
    geod = Geod(ellps='WGS84')
    
    # Calculate forward azimuth and distance
    azimuth, _, distance = geod.inv(lon0, lat0, lon1, lat1)
    
    # Calculate intermediate point at fraction alpha along the geodesic
    lon, lat, _ = geod.fwd(lon0, lat0, azimuth, alpha * distance)
    
    return (lon, lat)