"""Geodesic area of WGS84 (EPSG:4326) polygons.

Areas are computed on the WGS84 ellipsoid with pyproj's Geod (GeographicLib
polygon area algorithm), so results are accurate for polygons anywhere on
Earth, including those crossing the antimeridian or enclosing a pole.
Holes are subtracted; ring orientation is irrelevant.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Union

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import LinearRing

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    return Geod(ellps="WGS84")


def _ring_area_m2(ring: LinearRing) -> float:
    """Unsigned geodesic area enclosed by a single ring, in square meters."""
    if ring.is_empty:
        return 0.0
    lons, lats = ring.xy  # ignores any Z coordinate
    if len(lons) < 4:  # fewer than 3 distinct vertices plus closure
        return 0.0
    area, _perimeter = _geod().polygon_area_perimeter(lons, lats)
    return abs(float(area))


def _polygon_area_m2(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    area = _ring_area_m2(poly.exterior)
    for hole in poly.interiors:
        area -= _ring_area_m2(hole)
    return max(area, 0.0)


def area_m2(geom: Union[Polygon, MultiPolygon]) -> float:
    """Return the geodesic area of ``geom`` in square meters.

    ``geom`` must be a shapely ``Polygon`` or ``MultiPolygon`` with
    longitude/latitude coordinates in EPSG:4326 (WGS84). Interior rings
    (holes) are subtracted from the exterior area. Ring orientation does
    not matter. Empty geometries return ``0.0``.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(p) for p in geom.geoms))
    raise TypeError(
        f"area_m2 expects a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
    )