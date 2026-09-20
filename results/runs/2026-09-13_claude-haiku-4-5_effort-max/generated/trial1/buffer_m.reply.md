```python
from shapely.ops import transform
import pyproj


def buffer_m(geom, distance_m):
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    utm_zone = int((lon + 180) / 6) + 1
    utm_zone = max(1, min(60, utm_zone))
    
    epsg_utm = (32600 + utm_zone) if lat >= 0 else (32700 + utm_zone)
    
    crs_4326 = pyproj.CRS('EPSG:4326')
    crs_utm = pyproj.CRS(f'EPSG:{epsg_utm}')
    
    transformer_to_utm = pyproj.Transformer.from_crs(crs_4326, crs_utm, always_xy=True)
    transformer_to_4326 = pyproj.Transformer.from_crs(crs_utm, crs_4326, always_xy=True)
    
    geom_utm = transform(transformer_to_utm.transform, geom)
    geom_buffered = geom_utm.buffer(distance_m)
    return transform(transformer_to_4326.transform, geom_buffered)
```