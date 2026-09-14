```python
from shapely.geometry import LineString
from pyproj import Geodesic, Transformer
import numpy as np


def project_line(line, dst_epsg):
    coords = list(line.coords)
    if not coords:
        return LineString()
    
    geod = Geodesic.from_crs("EPSG:4326")
    max_chord_km = 1100
    
    densified = []
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        densified.append((lon1, lat1))
        
        result = geod.inv(lon1, lat1, lon2, lat2)
        azimuth, back_azimuth, distance_m = result
        distance_km = distance_m / 1000
        
        if distance_km > max_chord_km:
            num_segments = int(np.ceil(distance_km / max_chord_km))
            for j in range(1, num_segments):
                segment_distance = (distance_m / num_segments) * j
                lon, lat, _ = geod.fwd(lon1, lat1, azimuth, segment_distance)
                densified.append((lon, lat))
    
    densified.append(coords[-1])
    
    wgs84_line = LineString(densified)
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{dst_epsg}", always_xy=True)
    transformed_coords = [transformer.transform(lon, lat) for lon, lat in wgs84_line.coords]
    
    return LineString(transformed_coords)
```