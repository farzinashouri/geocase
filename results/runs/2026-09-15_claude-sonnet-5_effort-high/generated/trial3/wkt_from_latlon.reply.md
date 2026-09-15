```python
"""Convert WGS84 latitude/longitude coordinates to a WKT POINT string."""

from shapely.geometry import Point


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return a WKT POINT string for a WGS84 (lat, lon) location.

    WKT/GIS tools expect coordinates in (x, y) = (longitude, latitude)
    order, so the input order is swapped when building the point.
    """
    return Point(lon, lat).wkt
```