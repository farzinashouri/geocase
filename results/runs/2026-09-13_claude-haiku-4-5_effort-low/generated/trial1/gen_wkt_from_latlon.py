from shapely.geometry import Point


def wkt_from_latlon(lat, lon):
    """Convert WGS84 latitude and longitude to WKT POINT string.
    
    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
    
    Returns:
        WKT POINT string with coordinates in (lon, lat) order
    """
    point = Point(lon, lat)
    return point.wkt