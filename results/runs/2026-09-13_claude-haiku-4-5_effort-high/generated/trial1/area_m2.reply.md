```python
from shapely.ops import transform
from pyproj import Transformer


def area_m2(geom):
    """Calculate area in square meters for a WGS84 polygon."""
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    transformer = Transformer.from_proj(
        "EPSG:4326",
        f"+proj=laea +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs",
        always_xy=True
    )
    
    projected_geom = transform(transformer.transform, geom)
    return float(projected_geom.area)
```