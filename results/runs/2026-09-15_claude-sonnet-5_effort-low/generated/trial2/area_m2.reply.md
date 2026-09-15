```python
"""Area calculation for WGS84 (lon/lat) polygons in square meters."""

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

_GEOD = Geod(ellps="WGS84")


def area_m2(geom):
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(poly) for poly in geom.geoms))
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    raise TypeError(f"area_m2 expects a Polygon or MultiPolygon, got {type(geom).__name__}")


def _polygon_area_m2(polygon):
    exterior_area, _ = _GEOD.geometry_area_perimeter(polygon.exterior)
    area = abs(exterior_area)
    for interior in polygon.interiors:
        interior_area, _ = _GEOD.geometry_area_perimeter(interior)
        area -= abs(interior_area)
    return area
```