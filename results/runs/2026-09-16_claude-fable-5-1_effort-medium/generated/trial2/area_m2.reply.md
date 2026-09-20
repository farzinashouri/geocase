Here is the module. It uses pyproj's geodesic (Karney) polygon area on the WGS84 ellipsoid, which is accurate anywhere on Earth including near the poles, and it handles orientation, holes, multipolygons, and polygons larger than a hemisphere.

```python
"""Geodesic area of EPSG:4326 polygons on the WGS84 ellipsoid."""

from __future__ import annotations

import math

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient

__all__ = ["area_m2"]

_GEOD = Geod(ellps="WGS84")


def _ellipsoid_area() -> float:
    """Total surface area of the WGS84 ellipsoid in m^2."""
    a, b = _GEOD.a, _GEOD.b
    e = math.sqrt(1.0 - (b * b) / (a * a))
    return 2.0 * math.pi * a * a + math.pi * (b * b / e) * math.log((1.0 + e) / (1.0 - e))


_EARTH_AREA = _ellipsoid_area()


def _ring_area(coords) -> float:
    """Signed geodesic area (m^2) of a closed ring; positive when counter-clockwise."""
    coords = list(coords)
    if len(coords) < 4:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    area, _ = _GEOD.polygon_area_perimeter(lons, lats)
    return float(area)


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    # Exterior counter-clockwise, interiors clockwise.
    poly = orient(poly, sign=1.0)
    exterior = _ring_area(poly.exterior.coords)
    # GeographicLib folds signed areas into (-A/2, A/2]; a counter-clockwise
    # ring larger than a hemisphere therefore comes back negative.
    if exterior < 0.0:
        exterior += _EARTH_AREA
    holes = sum(abs(_ring_area(ring.coords)) for ring in poly.interiors)
    return max(exterior - holes, 0.0)


def area_m2(geom) -> float:
    """Return the geodesic area in square meters of a WGS84 Polygon or MultiPolygon.

    Coordinates must be (longitude, latitude) in EPSG:4326. Any Z values are
    ignored. Empty geometries return 0.0.
    """
    if geom is None or geom.is_empty:
        return 0.0
    if isinstance(geom, Polygon):
        return float(_polygon_area(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(p) for p in geom.geoms))
    raise TypeError(
        f"area_m2 expects a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
    )
```