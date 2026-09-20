```python
"""Convert WGS84 latitude/longitude coordinates to a WKT POINT string."""

from shapely.geometry import Point


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return a WKT POINT string for a WGS84 (lat, lon) location.

    WKT POINT coordinates are ordered (X Y), i.e. (longitude latitude),
    per the OGC Simple Features spec that GIS tools expect.
    """
    return Point(lon, lat).wkt
```