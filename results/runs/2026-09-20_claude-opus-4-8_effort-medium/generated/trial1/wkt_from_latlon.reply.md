```python
"""Build WKT POINT strings from WGS84 latitude/longitude.

Importing this module has no side effects.
"""


def wkt_from_latlon(lat, lon):
    """Return a WKT POINT for the given WGS84 latitude and longitude.

    Arguments are (lat, lon) — the order user-facing APIs conventionally use.
    WKT (and GIS tools generally) expect coordinates in X Y order, i.e.
    longitude first, then latitude, so the axes are swapped on output.
    """
    lat = float(lat)
    lon = float(lon)

    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range [-90, 90]: {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"longitude out of range [-180, 180]: {lon}")

    # WKT is X Y => longitude latitude.
    return f"POINT ({lon!r} {lat!r})"
```