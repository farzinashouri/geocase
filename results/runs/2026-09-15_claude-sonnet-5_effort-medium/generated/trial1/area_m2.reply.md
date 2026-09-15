```python
"""Compute geodesic area of WGS84 polygons in square meters."""

from shapely.geometry.base import BaseGeometry
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def _polygon_area_m2(polygon) -> float:
    area, _ = _GEOD.geometry_area_perimeter(polygon)
    return abs(area)


def area_m2(geom: BaseGeometry) -> float:
    """Return the area in square meters of a WGS84 Polygon or MultiPolygon."""
    geom_type = geom.geom_type
    if geom_type == "Polygon":
        return _polygon_area_m2(geom)
    if geom_type == "MultiPolygon":
        return sum(_polygon_area_m2(part) for part in geom.geoms)
    raise TypeError(f"Unsupported geometry type: {geom_type}")
```