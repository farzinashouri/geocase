from shapely.ops import transform
import pyproj


def buffer_m(geom, distance_m):
    """Buffer a geometry in EPSG:4326 by a distance in meters."""
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    zone = int((lon + 180) / 6) + 1
    zone = max(1, min(60, zone))
    
    utm_epsg = (32600 + zone) if lat >= 0 else (32700 + zone)
    
    wgs84 = pyproj.CRS('EPSG:4326')
    utm_crs = pyproj.CRS(f'EPSG:{utm_epsg}')
    
    transformer_to_utm = pyproj.Transformer.from_crs(wgs84, utm_crs, always_xy=True)
    geom_utm = transform(transformer_to_utm.transform, geom)
    
    buffered_utm = geom_utm.buffer(distance_m)
    
    transformer_to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84, always_xy=True)
    buffered_geom = transform(transformer_to_wgs84.transform, buffered_utm)
    
    return buffered_geom