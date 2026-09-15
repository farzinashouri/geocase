I'll implement this using pyproj's geodesic area calculation, which computes area directly on the WGS84 ellipsoid and is accurate globally (including near poles and the antimeridian) without needing a local projection.

```python
"""Compute geodesic area of WGS84 polygons in square meters."""

from __future__ import annotations

from shapely.geometry import MultiPolygon, Polygon
from pyproj import Geod


def _ring_area(geod: Geod, coords) -> float:
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    area, _ = geod.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(geod: Geod, polygon: Polygon) -> float:
    area = _ring_area(geod, polygon.exterior.coords)
    for interior in polygon.interiors:
        area -= _ring_area(geod, interior.coords)
    return area


def area_m2(geom) -> float:
    """Return the geodesic area in square meters of a WGS84 Polygon or MultiPolygon."""
    geod = Geod(ellps="WGS84")
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(geod, poly) for poly in geom.geoms))
    if isinstance(geom, Polygon):
        return float(_polygon_area(geod, geom))
    raise TypeError(f"Expected Polygon or MultiPolygon, got {type(geom).__name__}")
```