"""Convert WGS84 latitude/longitude coordinates to WKT POINT strings."""

from shapely.geometry import Point


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return a WKT POINT string for a WGS84 (lat, lon) location.

    WKT/OGC point ordering is (x y), i.e. (longitude latitude), which is
    the reverse of the (lat, lon) order this function accepts.
    """
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range: {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"longitude out of range: {lon}")

    return Point(lon, lat).wkt