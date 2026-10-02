from shapely.geometry import Point

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
        WKT representation, e.g. "POINT (-122.4194 37.7749)".
    """
    # Shapely expects coordinates in (x, y) order = (longitude, latitude)
    return Point(lon, lat).wkt