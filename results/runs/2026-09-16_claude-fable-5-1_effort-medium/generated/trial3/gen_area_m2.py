"""Geodesic area of EPSG:4326 (WGS84 lon/lat) polygons in square meters."""

from __future__ import annotations

from functools import lru_cache

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    # Created lazily so importing the module has no side effects.
    return Geod(ellps="WGS84")


def _ring_area(coords) -> float:
    """Unsigned geodesic area of a single closed ring given (lon, lat[, z]) tuples."""
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    if len(lons) < 3:
        return 0.0
    area, _perimeter = _geod().polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    total = _ring_area(poly.exterior.coords)
    for hole in poly.interiors:
        total -= _ring_area(hole.coords)
    return max(total, 0.0)


def area_m2(geom: BaseGeometry) -> float:
    """Return the geodesic area in square meters of a WGS84 lon/lat polygon.

    Parameters
    ----------
    geom : shapely Polygon or MultiPolygon
        Coordinates must be longitude/latitude degrees (EPSG:4326).

    Returns
    -------
    float
        Area on the WGS84 ellipsoid in m^2 (always >= 0). Holes are subtracted.
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