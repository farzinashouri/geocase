from pyproj import Geod
from shapely.geometry import Polygon, MultiPolygon

def area_m2(geom):
    """
    Calculate the geodesic area of a Polygon or MultiPolygon in square meters.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry with coordinates in EPSG:4326 (longitude, latitude).

    Returns
    -------
    float
        Area in square meters.
    """
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise TypeError("geom must be a Polygon or MultiPolygon")

    geod = Geod(ellps="WGS84")
    area, _ = geod.geometry_area_perimeter(geom)
    return abs(area)