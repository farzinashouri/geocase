```python
"""Compute geodesic area of WGS84 polygons in square meters."""

from pyproj import Geod
from shapely.geometry.base import BaseGeometry

_GEOD = Geod(ellps="WGS84")


def area_m2(geom: BaseGeometry) -> float:
    geom_type = geom.geom_type
    if geom_type == "Polygon":
        return _polygon_area_m2(geom)
    if geom_type == "MultiPolygon":
        return sum(_polygon_area_m2(poly) for poly in geom.geoms)
    raise TypeError(f"Unsupported geometry type: {geom_type}")


def _polygon_area_m2(polygon) -> float:
    exterior_area, _ = _GEOD.geometry_area_perimeter(polygon.exterior)
    area = abs(exterior_area)
    for interior in polygon.interiors:
        interior_area, _ = _GEOD.geometry_area_perimeter(interior)
        area -= abs(interior_area)
    return area
```