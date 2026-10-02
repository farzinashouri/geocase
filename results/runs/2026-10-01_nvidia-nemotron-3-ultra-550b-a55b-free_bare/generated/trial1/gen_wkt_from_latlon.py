"""Module for converting latitude/longitude to WKT POINT strings."""

def wkt_from_latlon(lat: float, lon: float) -> str:
    """
    Return a WKT POINT string for the given WGS84 latitude and longitude.

    The WKT standard uses (x, y) order, i.e., (longitude, latitude).
    This function formats the coordinates with sufficient precision for GIS tools.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees (WGS84).
    lon : float
        Longitude in decimal degrees (WGS84).

    Returns
    -------
    str
        WKT POINT string, e.g., "POINT (-122.4194 37.7749)".
    """
    # Use high precision formatting to avoid scientific notation and ensure accuracy
    lon_str = format(lon, ".15g")
    lat_str = format(lat, ".15g")
    return f"POINT ({lon_str} {lat_str})"