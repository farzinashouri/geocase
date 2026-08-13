from __future__ import annotations
from typing import Union
import shapely.geometry as sg
from pyproj import Geod

# Geodesic calculator for WGS84 ellipsoid
_geod = Geod(ellps="WGS84")


def _clean_ring(coords):
    """Remove duplicate closing vertex if present."""
    if len(coords) > 1 and coords[0] == coords[-1]:
        return coords[:-1]
    return coords


def _ring_area(coords):
    """Area of a single ring (exterior or interior) in square metres."""
    cleaned = _clean_ring(coords)
    if len(cleaned) < 3:
        return 0.0
    lons, lats = zip(*cleaned)
    area, _ = _geod.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(poly: sg.Polygon) -> float:
    """Area of a Polygon, exterior minus interior holes."""
    ext_area = _ring_area(list(poly.exterior.coords))
    holes_area = sum(_ring_area(list(interior.coords)) for interior in poly.interiors)
    return ext_area - holes_area


def area_m2(geom: Union[sg.Polygon, sg.MultiPolygon]) -> float:
    """
    Return the geodesic area of a Shapely Polygon or MultiPolygon
    whose coordinates are longitude/latitude (EPSG:4326) in square metres.

    Parameters
    ----------
    geom : shapely.Polygon or shapely.MultiPolygon
        Geometry in EPSG:4326 (lon/lat).

    Returns
    -------
    float
        Area in square metres.
    """
    if isinstance(geom, sg.Polygon):
        return _polygon_area(geom)
    if isinstance(geom, sg.MultiPolygon):
        return sum(_polygon_area(p) for p in geom.geoms)
    raise TypeError("geom must be a shapely Polygon or MultiPolygon")