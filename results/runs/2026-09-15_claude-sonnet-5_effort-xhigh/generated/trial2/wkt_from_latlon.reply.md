```python
"""Convert WGS84 latitude/longitude coordinates to WKT POINT strings."""

from shapely import Point, to_wkt


def wkt_from_latlon(lat: float, lon: float) -> str:
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range: {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"longitude out of range: {lon}")
    return to_wkt(Point(lon, lat), rounding_precision=-1)
```