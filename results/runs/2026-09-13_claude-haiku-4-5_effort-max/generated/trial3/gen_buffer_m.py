from shapely.ops import transform
from pyproj import Transformer

def buffer_m(geom, distance_m):
    """
    Buffer a WGS84 geometry by a distance in meters.
    
    Projects to UTM for buffering (which requires metric coordinates),
    then projects back to WGS84.
    """
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    utm_zone = int((lon + 180) / 6) + 1
    utm_epsg = 32600 + utm_zone if lat >= 0 else 32700 + utm_zone
    
    to_utm = Transformer.from_crs(4326, utm_epsg, always_xy=True)
    from_utm = Transformer.from_crs(utm_epsg, 4326, always_xy=True)
    
    geom_utm = transform(to_utm.transform, geom)
    geom_buffered = geom_utm.buffer(distance_m)
    return transform(from_utm.transform, geom_buffered)