```python
"""Convert WGS84 latitude/longitude pairs to WKT POINT strings."""

from shapely.geometry import Point


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return a WKT POINT string for a WGS84 location.

    Args:
        lat: Latitude in decimal degrees (-90 to 90).
        lon: Longitude in decimal degrees (-180 to 180).

    Returns:
        A WKT string like "POINT (lon lat)". WKT/GIS tools expect
        coordinates in (x, y) = (longitude, latitude) order, which is
        the reverse of the (lat, lon) order this function accepts.
    """
    if not -90 <= lat <= 90:
        raise ValueError(f"latitude out of range: {lat}")
    if not -180 <= lon <= 180:
        raise ValueError(f"longitude out of range: {lon}")

    return Point(lon, lat).wkt
```