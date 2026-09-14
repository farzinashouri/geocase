import bisect
from pyproj import Geod

def position_at(fixes, t):
    timestamps = [f[0] for f in fixes]
    idx = bisect.bisect_right(timestamps, t)
    
    if idx == 0:
        return (fixes[0][1], fixes[0][2])
    if idx >= len(fixes):
        return (fixes[-1][1], fixes[-1][2])
    
    t1, lon1, lat1 = fixes[idx - 1]
    t2, lon2, lat2 = fixes[idx]
    
    if t1 == t2:
        return (lon1, lat1)
    
    time_frac = (t - t1) / (t2 - t1)
    
    geod = Geod(ellps='WGS84')
    az12, _, distance = geod.inv(lon1, lat1, lon2, lat2)
    lon_result, lat_result, _ = geod.fwd(lon1, lat1, az12, distance * time_frac)
    
    return (lon_result, lat_result)