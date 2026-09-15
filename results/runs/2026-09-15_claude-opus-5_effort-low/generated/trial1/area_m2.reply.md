```python
"""Geodesic area of WGS84 (EPSG:4326) polygons, in square meters.

Uses pyproj's geodesic (Karney) area computation on the WGS84 ellipsoid, so
results are accurate anywhere on Earth without picking a projected CRS.
"""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]

_GEOD = Geod(ellps="WGS84")


def _ring_area_m2(coords) -> float:
    """Unsigned geodesic area enclosed by a single closed ring."""
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    if len(lons) < 4:  # fewer than 3 distinct vertices encloses nothing
        return 0.0
    area, _perimeter = _GEOD.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area_m2(polygon) -> float:
    area = _ring_area_m2(polygon.exterior.coords)
    for interior in polygon.interiors:
        area -= _ring_area_m2(interior.coords)
    return area


def area_m2(geom: BaseGeometry) -> float:
    """Return the area of a lon/lat ``Polygon``/``MultiPolygon`` in m**2.

    Args:
        geom: A shapely ``Polygon`` or ``MultiPolygon`` with coordinates in
            EPSG:4326 (x = longitude, y = latitude, in degrees).

    Returns:
        The geodesic area on the WGS84 ellipsoid, in square meters. Holes are
        subtracted; the result is never negative regardless of ring winding.
    """
    if geom is None or geom.is_empty:
        return 0.0

    geom_type = geom.geom_type
    if geom_type == "Polygon":
        total = _polygon_area_m2(geom)
    elif geom_type == "MultiPolygon":
        total = sum(_polygon_area_m2(part) for part in geom.geoms)
    else:
        raise TypeError(
            f"area_m2 expects a Polygon or MultiPolygon, got {geom_type}"
        )

    return float(max(total, 0.0))
```