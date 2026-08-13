```python
"""
Utility module for converting latitude/longitude coordinates to a WKT POINT string.

The function `wkt_from_latlon` accepts latitude and longitude in that order
and returns a WKT string that can be loaded by most GIS tools.
"""

__all__ = ["wkt_from_latlon"]


def wkt_from_latlon(lat, lon):
    """
    Convert latitude and longitude (WGS84) to a WKT POINT string.

    Parameters
    ----------
    lat : float or int
        Latitude in degrees.
    lon : float or int
        Longitude in degrees.

    Returns
    -------
    str
        WKT representation of the point, e.g. "POINT(lon lat)".

    Raises
    ------
    TypeError
        If either latitude or longitude cannot be converted to a float.
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError) as exc:
        raise TypeError("Latitude and longitude must be numeric values.") from exc

    return f"POINT({lon} {lat})"
```