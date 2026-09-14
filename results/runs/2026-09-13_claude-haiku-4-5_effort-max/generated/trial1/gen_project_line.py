from shapely.geometry import LineString
from pyproj import Geod, Transformer
import numpy as np

def project_line(line, dst_epsg):
    coords = list(line.coords)
    geod = Geod(ellps='WGS84')
    transformer = Transformer.from_crs(4326, dst_epsg)
    
    all_vertices = []
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        az12, az21, dist = geod.inv(lon1, lat1, lon2, lat2)
        
        if i == 0:
            all_vertices.append((lon1, lat1))
        
        num_segments = max(1, int(np.ceil(dist / 50000)))
        
        for j in range(1, num_segments + 1):
            frac = j / num_segments
            lon_int, lat_int, _ = geod.fwd(lon1, lat1, az12, frac * dist)
            all_vertices.append((lon_int, lat_int))
    
    projected_coords = [transformer.transform(lon, lat) for lon, lat in all_vertices]
    
    return LineString(projected_coords)