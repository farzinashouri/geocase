from shapely.ops import transform
from pyproj import Transformer


def buffer_m(geom, distance_m):
    """
    Buffer a WGS84 geometry by a distance in meters.
    
    Args:
        geom: A shapely geometry with EPSG:4326 coordinates
        distance_m: Buffer distance in meters
        
    Returns:
        A buffered geometry with EPSG:4326 coordinates
    """
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y
    
    # Calculate UTM zone from centroid
    zone = int((lon + 180) / 6) + 1
    zone = min(zone, 60)
    
    is_south = lat < 0
    epsg_code = 32700 + zone if is_south else 32600 + zone
    
    # Transform to UTM, buffer, and transform back
    to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_code}", always_xy=True)
    to_wgs84 = Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)
    
    geom_utm = transform(to_utm.transform, geom)
    geom_buffered = geom_utm.buffer(distance_m)
    return transform(to_wgs84.transform, geom_buffered)