```python
"""Build a WKT POINT string from a WGS84 latitude/longitude pair."""


def wkt_from_latlon(lat, lon):
    """Return a WKT POINT for the given WGS84 latitude and longitude.

    Args:
        lat: Latitude in WGS84 decimal degrees.
        lon: Longitude in WGS84 decimal degrees.

    Returns:
        A WKT ``POINT`` string. WKT (like most GIS coordinate order
        conventions) is X Y, i.e. longitude first then latitude, even
        though this API takes latitude first to match user-facing usage.
    """
    lat = float(lat)
    lon = float(lon)

    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range [-90, 90]: {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"longitude out of range [-180, 180]: {lon}")

    # WKT coordinate order is X (longitude) then Y (latitude).
    return f"POINT ({lon!r} {lat!r})"
```