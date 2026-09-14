from pyproj import Geodesic
import bisect


def position_at(fixes, t):
    timestamps = [fix[0] for fix in fixes]
    idx = bisect.bisect_right(timestamps, t) - 1
    
    t1, lon1, lat1 = fixes[idx]
    t2, lon2, lat2 = fixes[idx + 1]
    
    alpha = (t - t1) / (t2 - t1)
    
    geod = Geodesic(ellps='WGS84')
    s12, az12, _ = geod.inv(lon1, lat1, lon2, lat2)
    
    intermediate_distance = s12 * alpha
    lon, lat, _ = geod.fwd(lon1, lat1, az12, intermediate_distance)
    
    return (lon, lat)