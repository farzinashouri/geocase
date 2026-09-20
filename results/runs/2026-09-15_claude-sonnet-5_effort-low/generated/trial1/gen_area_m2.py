"""Compute geodesic area of shapely geometries in EPSG:4326."""

from pyproj import Geod
from shapely.geometry.base import BaseGeometry

_GEOD = Geod(ellps="WGS84")


def area_m2(geom: BaseGeometry) -> float:
    """Return the geodesic area in square meters of a Polygon or MultiPolygon
    whose coordinates are lon/lat in EPSG:4326."""
    geom_type = geom.geom_type

    if geom_type == "Polygon":
        polygons = [geom]
    elif geom_type == "MultiPolygon":
        polygons = list(geom.geoms)
    else:
        raise TypeError(f"Unsupported geometry type: {geom_type}")

    total = 0.0
    for polygon in polygons:
        exterior_area, _ = _GEOD.geometry_area_perimeter(polygon.exterior)
        total += abs(exterior_area)
        for interior in polygon.interiors:
            interior_area, _ = _GEOD.geometry_area_perimeter(interior)
            total -= abs(interior_area)

    return float(total)