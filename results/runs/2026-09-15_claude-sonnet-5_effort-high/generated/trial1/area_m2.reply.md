```python
"""Compute geodesic area of longitude/latitude polygons on the WGS84 ellipsoid."""

from shapely.geometry import MultiPolygon, Polygon
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def _polygon_area_m2(polygon: Polygon) -> float:
    area, _perimeter = _GEOD.geometry_area_perimeter(polygon)
    return abs(area)


def area_m2(geom) -> float:
    """Return the area in square meters of a lon/lat (EPSG:4326) Polygon or MultiPolygon."""
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(part) for part in geom.geoms))
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    raise TypeError(f"area_m2 expects a Polygon or MultiPolygon, got {type(geom).__name__}")
```