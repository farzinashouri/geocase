```python
from shapely.geometry import Point

def wkt_from_latlon(lat, lon):
    """Convert latitude and longitude to WKT POINT string.
    
    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        
    Returns:
        WKT POINT string for use in GIS tools
    """
    point = Point(lon, lat)
    return point.wkt
```