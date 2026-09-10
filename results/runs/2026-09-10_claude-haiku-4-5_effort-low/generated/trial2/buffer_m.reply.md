```python
from shapely.ops import transform
import pyproj


def buffer_m(geom, distance_m):
    if geom.is_empty:
        return geom
    
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    utm_zone = int((lon + 180) / 6) + 1
    epsg_code = (32600 + utm_zone) if lat >= 0 else (32700 + utm_zone)
    
    wgs84 = pyproj.CRS('EPSG:4326')
    utm_crs = pyproj.CRS(f'EPSG:{epsg_code}')
    
    to_utm = pyproj.Transformer.from_crs(wgs84, utm_crs, always_xy=True)
    to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84, always_xy=True)
    
    geom_utm = transform(to_utm.transform, geom)
    geom_buffered = geom_utm.buffer(distance_m)
    
    return transform(to_wgs84.transform, geom_buffered)
```