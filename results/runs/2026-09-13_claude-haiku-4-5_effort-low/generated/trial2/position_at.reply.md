```python
from pyproj import Geod
from typing import List, Tuple

def position_at(fixes: List[Tuple[float, float, float]], t: float) -> Tuple[float, float]:
    """
    Estimate ship position at time t using geodesic interpolation between GPS fixes.
    
    Args:
        fixes: Chronologically sorted list of (timestamp, lon, lat) tuples (WGS84)
        t: Target timestamp
    
    Returns:
        Interpolated (lon, lat) position at time t
    """
    # Find the two fixes bracketing time t
    for i in range(len(fixes) - 1):
        if fixes[i][0] <= t <= fixes[i + 1][0]:
            t0, lon0, lat0 = fixes[i]
            t1, lon1, lat1 = fixes[i + 1]
            break
    else:
        raise ValueError("Time t not between first and last fix")
    
    # Handle edge cases
    if t == t0:
        return (lon0, lat0)
    if t == t1:
        return (lon1, lat1)
    
    # Linear interpolation in time
    alpha = (t - t0) / (t1 - t0)
    
    # Geodesic interpolation between the two fixes
    geod = Geod(ellps='WGS84')
    
    # Get forward azimuth and distance from fix0 to fix1
    az12, _, dist = geod.inv(lon0, lat0, lon1, lat1)
    
    # Move alpha fraction of the distance along the geodesic
    lon_interp, lat_interp, _ = geod.fwd(lon0, lat0, az12, dist * alpha)
    
    return (lon_interp, lat_interp)
```