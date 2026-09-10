```python
import bisect
from pyproj import Geod

def position_at(fixes, t):
    """
    Estimate ship position at time t using geodetic interpolation.
    
    Args:
        fixes: List of (timestamp, lon, lat) tuples, chronologically sorted
        t: Timestamp (Unix seconds) at which to estimate position
    
    Returns:
        (lon, lat) tuple of estimated position
    """
    timestamps = [f[0] for f in fixes]
    idx = bisect.bisect_left(timestamps, t)
    
    if idx == 0:
        return (fixes[0][1], fixes[0][2])
    if idx >= len(fixes):
        return (fixes[-1][1], fixes[-1][2])
    
    fix_before = fixes[idx - 1]
    fix_after = fixes[idx]
    
    t1, lon1, lat1 = fix_before
    t2, lon2, lat2 = fix_after
    
    fraction = (t - t1) / (t2 - t1)
    
    geod = Geod(ellps='WGS84')
    azimuth, _, distance = geod.inv(lon1, lat1, lon2, lat2)
    interpolated_lon, interpolated_lat = geod.fwd(lon1, lat1, azimuth, fraction * distance)
    
    return (interpolated_lon, interpolated_lat)
```