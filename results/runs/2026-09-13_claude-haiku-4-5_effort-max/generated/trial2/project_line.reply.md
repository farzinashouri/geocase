```python
import numpy as np
from shapely.geometry import LineString
from pyproj import Geod, Transformer

def project_line(line, dst_epsg):
    coords = list(line.coords)
    
    geod = Geod(ellps='WGS84')
    transformer = Transformer.from_crs(4326, dst_epsg, always_xy=True)
    
    output_points = []
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        _, _, dist_m = geod.inv(lon1, lat1, lon2, lat2)
        dist_km = dist_m / 1000.0
        
        n_segments = max(1, int(np.ceil(dist_km / 1128.0)))
        
        pts = geod.npts(lon1, lat1, lon2, lat2, n_segments + 1)
        
        for j, (lon, lat) in enumerate(pts):
            if j == 0 and i > 0:
                continue
            x, y = transformer.transform(lon, lat)
            output_points.append((x, y))
    
    return LineString(output_points)
```