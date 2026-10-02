def wkt_from_latlon(lat, lon):
    """
    Return a WKT POINT string for the given latitude and longitude (WGS84).

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees.
    lon : float
        Longitude in decimal degrees.

    Returns
    -------
    str
        WKT POINT string, e.g., 'POINT (longitude latitude)'.
    """
    return f"POINT ({lon} {lat})"