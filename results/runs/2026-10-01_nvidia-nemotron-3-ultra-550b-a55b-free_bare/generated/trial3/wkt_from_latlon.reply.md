```python
"""Module for converting latitude/longitude to WKT POINT strings."""

def wkt_from_latlon(lat: float, lon: float) -> str:
    """
    Return a WKT POINT string for the given WGS84 latitude and longitude.

    The WKT standard expects coordinates in (longitude, latitude) order.
    This function accepts (lat, lon) as per common user-facing APIs and
    returns a string formatted as 'POINT (lon lat)'.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees (WGS84).
    lon : float
        Longitude in decimal degrees (WGS84).

    Returns
    -------
    str
        WKT POINT string, e.g., 'POINT (-122.4194 37.7749)'.
    """
    return f"POINT ({lon} {lat})"
```