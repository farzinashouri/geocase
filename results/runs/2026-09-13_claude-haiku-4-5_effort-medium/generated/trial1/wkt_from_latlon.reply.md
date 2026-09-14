```python
from shapely.geometry import Point

def wkt_from_latlon(lat, lon):
    """Convert WGS84 latitude and longitude to WKT POINT string."""
    point = Point(lon, lat)
    return point.wkt
```