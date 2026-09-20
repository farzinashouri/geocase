```python
"""Geodesic area computation for WGS84 (EPSG:4326) polygons."""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

_GEOD = Geod(ellps="WGS84")


def _ring_area(coords) -> float:
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    area, _ = _GEOD.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(polygon: Polygon) -> float:
    area = _ring_area(polygon.exterior.coords)
    for interior in polygon.interiors:
        area -= _ring_area(interior.coords)
    return area


def area_m2(geom) -> float:
    """Return the geodesic area in square meters of a lon/lat Polygon or MultiPolygon."""
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(poly) for poly in geom.geoms))
    if isinstance(geom, Polygon):
        return float(_polygon_area(geom))
    raise TypeError(f"area_m2 expects a Polygon or MultiPolygon, got {type(geom)!r}")
```