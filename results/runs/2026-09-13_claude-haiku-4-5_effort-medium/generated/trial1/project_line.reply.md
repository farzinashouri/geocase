```python
from shapely.geometry import LineString
from pyproj import Geod, Transformer
import math

def project_line(line, dst_epsg):
    coords = list(line.coords)
    
    if len(coords) < 2:
        transformer = Transformer.from_crs('EPSG:4326', f'EPSG:{dst_epsg}', always_xy=True)
        projected = [transformer.transform(lon, lat) for lon, lat in coords]
        return LineString(projected)
    
    geod = Geod(ellps='WGS84')
    dense_coords = []
    max_segment_m = 1_000_000
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        dense_coords.append((lon1, lat1))
        
        distance_m, az_forward, _ = geod.inv(lon1, lat1, lon2, lat2)
        n_segments = max(1, math.ceil(distance_m / max_segment_m))
        
        for j in range(1, n_segments):
            frac = j / n_segments
            lon_int, lat_int, _ = geod.fwd(lon1, lat1, az_forward, distance_m * frac)
            dense_coords.append((lon_int, lat_int))
    
    dense_coords.append(coords[-1])
    
    transformer = Transformer.from_crs('EPSG:4326', f'EPSG:{dst_epsg}', always_xy=True)
    projected_coords = [transformer.transform(lon, lat) for lon, lat in dense_coords]
    
    return LineString(projected_coords)
```