"""Compute geodesic area of WGS84 polygons using pyproj's authalic-sphere algorithm."""

from shapely.geometry.base import BaseGeometry
from shapely.geometry import Polygon, MultiPolygon
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def _ring_area(coords) -> float:
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    area, _ = _GEOD.polygon_area_perimeter(lons, lats)
    return area


def _polygon_area(polygon: Polygon) -> float:
    area = abs(_ring_area(list(polygon.exterior.coords)))
    for interior in polygon.interiors:
        area -= abs(_ring_area(list(interior.coords)))
    return area


def area_m2(geom: BaseGeometry) -> float:
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(poly) for poly in geom.geoms))
    if isinstance(geom, Polygon):
        return float(_polygon_area(geom))
    raise TypeError(f"Unsupported geometry type: {type(geom)!r}")