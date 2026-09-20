```python
from shapely.ops import transform
import pyproj
import numpy as np

def buffer_m(geom, distance_m):
    centroid = geom.centroid
    
    wgs84 = pyproj.Proj(proj='latlong', datum='WGS84')
    aeqd = pyproj.Proj(proj='aeqd', lat_0=centroid.y, lon_0=centroid.x)
    
    to_aeqd = pyproj.Transformer.from_proj(wgs84, aeqd, always_xy=True)
    from_aeqd = pyproj.Transformer.from_proj(aeqd, wgs84, always_xy=True)
    
    def to_aeqd_func(coords):
        x, y = coords[:, 0], coords[:, 1]
        x_proj, y_proj = to_aeqd.transform(x, y)
        return np.column_stack([x_proj, y_proj])
    
    def from_aeqd_func(coords):
        x, y = coords[:, 0], coords[:, 1]
        x_proj, y_proj = from_aeqd.transform(x, y)
        return np.column_stack([x_proj, y_proj])
    
    geom_proj = transform(to_aeqd_func, geom)
    geom_buffered = geom_proj.buffer(distance_m)
    return transform(from_aeqd_func, geom_buffered)
```