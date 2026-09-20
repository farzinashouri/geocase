```python
from shapely.ops import transform
from pyproj import Transformer, CRS


def buffer_m(geom, distance_m):
    """
    Buffer a WGS84 geometry by distance in meters.
    
    Projects to a local UTM zone, buffers in meters, and projects back to EPSG:4326.
    """
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    utm_zone = int((lon + 180) / 6) + 1
    utm_epsg = (32600 + utm_zone) if lat >= 0 else (32700 + utm_zone)
    
    wgs84_crs = CRS.from_epsg(4326)
    utm_crs = CRS.from_epsg(utm_epsg)
    
    to_utm = Transformer.from_crs(wgs84_crs, utm_crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(utm_crs, wgs84_crs, always_xy=True)
    
    utm_geom = transform(lambda x, y, z=None: to_utm.transform(x, y, z), geom)
    buffered_utm = utm_geom.buffer(distance_m)
    result = transform(lambda x, y, z=None: to_wgs84.transform(x, y, z), buffered_utm)
    
    return result
```