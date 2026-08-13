"""
Utility module for converting latitude/longitude coordinates to a WKT POINT string.

The function `wkt_from_latlon` accepts latitude and longitude in WGS84
(e.g., lat, lon) and returns a WKT string that can be loaded by standard GIS tools.
"""

from shapely.geometry import Point


def wkt_from_latlon(lat: float, lon: float) -> str:
    """
    Convert latitude and longitude to a WKT POINT string.

    Parameters
    ----------
    lat : float
        Latitude in degrees (WGS84).
    lon : float
        Longitude in degrees (WGS84).

    Returns
    -------
    str
        A WKT representation of the point, e.g., "POINT (lon lat)".
    """
    return Point(lon, lat).wkt