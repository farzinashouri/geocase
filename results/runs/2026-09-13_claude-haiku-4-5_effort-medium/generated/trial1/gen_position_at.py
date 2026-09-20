from pyproj import Geod

def position_at(fixes, t):
    """
    Estimate ship position at time t via geodesic interpolation.
    
    Args:
        fixes: Chronologically sorted list of (timestamp, lon, lat) tuples
               where timestamps are Unix seconds and positions are WGS84.
        t: Target timestamp between first and last fix.
        
    Returns:
        (lon, lat) tuple of interpolated position in WGS84.
    """
    # Find fixes bracketing time t
    for i in range(len(fixes) - 1):
        t1, lon1, lat1 = fixes[i]
        t2, lon2, lat2 = fixes[i + 1]
        
        if not (t1 <= t <= t2):
            continue
        
        if t == t1:
            return (lon1, lat1)
        if t == t2:
            return (lon2, lat2)
        
        # Interpolation factor
        alpha = (t - t1) / (t2 - t1)
        
        # Calculate geodesic distance and bearing
        geod = Geod(ellps='WGS84')
        az_fwd, az_back, distance = geod.inv(lon1, lat1, lon2, lat2)
        
        # Interpolate along the geodesic
        lon_result, lat_result, _ = geod.fwd(lon1, lat1, az_fwd, alpha * distance)
        return (lon_result, lat_result)
    
    raise ValueError(f"Time {t} outside range of fixes")