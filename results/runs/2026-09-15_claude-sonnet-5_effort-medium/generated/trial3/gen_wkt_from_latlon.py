from shapely.geometry import Point


def wkt_from_latlon(lat: float, lon: float) -> str:
    """Return WKT POINT for WGS84 lat/lon, in the WKT-mandated lon/lat axis order."""
    return Point(lon, lat).wkt