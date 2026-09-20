from pyproj import Geod
import bisect


def position_at(fixes, t):
    timestamps = [f[0] for f in fixes]
    idx = bisect.bisect_right(timestamps, t)
    
    if idx == 0:
        return fixes[0][1:3]
    if idx == len(fixes):
        return fixes[-1][1:3]
    
    t1, lon1, lat1 = fixes[idx - 1]
    t2, lon2, lat2 = fixes[idx]
    time_fraction = (t - t1) / (t2 - t1)
    
    geod = Geod(ellps='WGS84')
    azimuth, _, distance = geod.inv(lon1, lat1, lon2, lat2)
    lon_interp, lat_interp, _ = geod.fwd(lon1, lat1, azimuth, distance * time_fraction)
    
    return (lon_interp, lat_interp)