```python
from pyproj import Geodesic

def position_at(fixes, t):
    """
    Estimate ship position at time t using geodetic interpolation.
    
    Args:
        fixes: List of (timestamp, lon, lat) tuples, sorted chronologically
        t: Target timestamp
        
    Returns:
        (lon, lat) tuple estimated position at time t
    """
    for i in range(len(fixes) - 1):
        t1, lon1, lat1 = fixes[i]
        t2, lon2, lat2 = fixes[i + 1]
        
        if t1 <= t <= t2:
            if t == t1:
                return (lon1, lat1)
            if t == t2:
                return (lon2, lat2)
            
            geod = Geodesic.WGS84
            fraction = (t - t1) / (t2 - t1)
            
            inv = geod.Inverse(lat1, lon1, lat2, lon2)
            distance = inv['s12'] * fraction
            
            pos = geod.Direct(lat1, lon1, inv['azi1'], distance)
            return (pos['lon2'], pos['lat2'])
    
    raise ValueError(f"Time {t} is outside the range of fixes")
```