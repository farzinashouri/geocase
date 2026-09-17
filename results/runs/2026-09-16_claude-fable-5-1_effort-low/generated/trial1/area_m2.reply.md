```python
"""Geodesic area of EPSG:4326 (WGS84) polygons in square meters.

Uses pyproj's Geod, which computes areas on the WGS84 ellipsoid via
Karney's algorithms, so results are accurate anywhere on Earth, including
polygons that cross the antimeridian or enclose a pole.
"""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

__all__ = ["area_m2"]

_GEOD = Geod(ellps="WGS84")


def _ring_area(coords) -> float:
    """Unsigned geodesic area of a single closed ring (lon/lat pairs)."""
    lons = [float(c[0]) for c in coords]
    lats = [float(c[1]) for c in coords]
    if len(lons) < 3:
        return 0.0
    area, _perimeter = _GEOD.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    area = _ring_area(poly.exterior.coords)
    for interior in poly.interiors:
        area -= _ring_area(interior.coords)
    return max(area, 0.0)


def area_m2(geom) -> float:
    """Return the geodesic area in square meters of a WGS84 Polygon/MultiPolygon.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry with coordinates as (longitude, latitude) in EPSG:4326.

    Returns
    -------
    float
        Area in square meters (always non-negative).

    Raises
    ------
    TypeError
        If ``geom`` is not a Polygon or MultiPolygon.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(p) for p in geom.geoms))
    raise TypeError(
        f"area_m2 expects a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
    )
```