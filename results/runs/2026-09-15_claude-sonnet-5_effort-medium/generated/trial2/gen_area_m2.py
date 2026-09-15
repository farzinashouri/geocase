"""Compute the geodesic area of a WGS84 polygon or multipolygon."""

from pyproj import Geod
from shapely.geometry.base import BaseGeometry

_GEOD = Geod(ellps="WGS84")


def area_m2(geom: BaseGeometry) -> float:
    """Return the area in square meters of a lon/lat (EPSG:4326) Polygon or MultiPolygon."""
    geom_type = geom.geom_type

    if geom_type == "Polygon":
        return _polygon_area_m2(geom)

    if geom_type == "MultiPolygon":
        return sum(_polygon_area_m2(part) for part in geom.geoms)

    raise TypeError(f"Unsupported geometry type: {geom_type!r}")


def _polygon_area_m2(polygon) -> float:
    exterior_area, _ = _GEOD.geometry_area_perimeter(polygon.exterior)
    area = abs(exterior_area)

    for interior in polygon.interiors:
        hole_area, _ = _GEOD.geometry_area_perimeter(interior)
        area -= abs(hole_area)

    return area