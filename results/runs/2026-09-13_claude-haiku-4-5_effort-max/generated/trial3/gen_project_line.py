import numpy as np
from shapely.geometry import LineString
from pyproj import Geod, Transformer


def project_line(line, dst_epsg):
    coords = list(line.coords)
    
    geod = Geod(ellps='WGS84')
    transformer = Transformer.from_epsg_code(4326, dst_epsg, always_xy=True)
    
    projected_coords = []
    max_segment_dist = 25000  # 25 km in meters
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        az12, az21, distance_m = geod.inv(lon1, lat1, lon2, lat2)
        num_segments = max(1, int(np.ceil(distance_m / max_segment_dist)))
        
        for j in range(num_segments):
            segment_dist = j * (distance_m / num_segments)
            lon, lat = geod.fwd(lon1, lat1, az12, segment_dist)[:2]
            x, y = transformer.transform(lon, lat)
            projected_coords.append((x, y))
    
    lon, lat = coords[-1]
    x, y = transformer.transform(lon, lat)
    projected_coords.append((x, y))
    
    return LineString(projected_coords)