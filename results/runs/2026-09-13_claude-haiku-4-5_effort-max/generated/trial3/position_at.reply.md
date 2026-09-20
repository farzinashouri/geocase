```python
from pyproj import Geod


def position_at(fixes, t):
    """
    Estimate ship position at time t by interpolating GPS fixes.
    
    Args:
        fixes: List of (timestamp, lon, lat) tuples, chronologically sorted.
        t: Target timestamp (Unix seconds) between first and last fix times.
    
    Returns:
        (lon, lat) tuple of estimated position in WGS84.
    """
    for i in range(len(fixes) - 1):
        if fixes[i][0] <= t <= fixes[i + 1][0]:
            t1, lon1, lat1 = fixes[i]
            t2, lon2, lat2 = fixes[i + 1]
            break
    else:
        raise ValueError("Time t is outside the range of fixes")
    
    if t == t1:
        return (lon1, lat1)
    if t == t2:
        return (lon2, lat2)
    
    alpha = (t - t1) / (t2 - t1)
    geod = Geod(ellps='WGS84')
    bearing, _, distance = geod.inv(lon1, lat1, lon2, lat2)
    lon_result, lat_result, _ = geod.fwd(lon1, lat1, bearing, distance * alpha)
    
    return (lon_result, lat_result)
```