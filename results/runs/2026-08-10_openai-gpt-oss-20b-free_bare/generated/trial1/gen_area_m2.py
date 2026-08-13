"""
Module providing a function to compute the area of a shapely Polygon or MultiPolygon
in square metres, assuming the coordinates are in EPSG:4326 (WGS84).
"""

from __future__ import annotations

from shapely.geometry import Polygon, MultiPolygon
from pyproj import Geod

# WGS84 ellipsoid for accurate geodesic calculations
_geod = Geod(ellps="WGS84")


def area_m2(geom: Polygon | MultiPolygon) -> float:
    """
    Calculate the area of a Polygon or MultiPolygon in square metres.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry with longitude/latitude coordinates in EPSG:4326.

    Returns
    -------
    float
        The area in square metres.

    Raises
    ------
    TypeError
        If the input geometry is not a Polygon or MultiPolygon.
    """
    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    else:
        raise TypeError("geom must be a shapely Polygon or MultiPolygon")

    total_area = 0.0

    for poly in polys:
        # Exterior ring
        ex_lons, ex_lats = zip(*poly.exterior.coords)
        area_ex, _ = _geod.polygon_area_perimeter(ex_lons, ex_lats)
        area_ex = abs(area_ex)

        # Subtract holes (interior rings)
        area_holes = 0.0
        for interior in poly.interiors:
            in_lons, in_lats = zip(*interior.coords)
            area_in, _ = _geod.polygon_area_perimeter(in_lons, in_lats)
            area_holes += abs(area_in)

        total_area += area_ex - area_holes

    return float(total_area)