"""Module for computing geodesic area of shapely geometries in square meters."""

from pyproj import Geod

# Pre-create a Geod instance for WGS84 to avoid overhead on each call.
_GEOD = Geod(ellps="WGS84")

def area_m2(geom):
    """
    Calculate the area of a shapely Polygon or MultiPolygon in square meters.

    Parameters
    ----------
    geom : shapely.Polygon or shapely.MultiPolygon
        Geometry in EPSG:4326 (longitude/latitude, WGS84).

    Returns
    -------
    float
        Area in square meters.
    """
    area, _ = _GEOD.geometry_area_perimeter(geom)
    return abs(area)