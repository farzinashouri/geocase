"""Geodesic area for WGS84 (EPSG:4326) polygons.

Areas are computed on the WGS84 ellipsoid with pyproj's geodesic routines, so
they are accurate anywhere on Earth (poles, antimeridian-spanning rings, very
large polygons) without picking a projected CRS.
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import Geod
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """Return a cached WGS84 Geod (built on first use, not at import time)."""
    return Geod(ellps="WGS84")


def _polygon_area_m2(polygon) -> float:
    """Absolute geodesic area of a single Polygon, holes subtracted."""
    geod = _geod()
    exterior, _ = geod.geometry_area_perimeter(polygon.exterior)
    area = abs(exterior)
    for interior in polygon.interiors:
        hole, _ = geod.geometry_area_perimeter(interior)
        area -= abs(hole)
    return area


def area_m2(geom: BaseGeometry) -> float:
    """Geodesic area in square meters of a lon/lat Polygon or MultiPolygon.

    Args:
        geom: A shapely Polygon or MultiPolygon with coordinates ordered
            (longitude, latitude) in degrees, EPSG:4326.

    Returns:
        The area in square meters. Always non-negative; ring winding order is
        ignored and interior rings (holes) are subtracted.

    Raises:
        TypeError: If ``geom`` is not a Polygon or MultiPolygon.
    """
    geom_type = getattr(geom, "geom_type", None)

    if geom_type == "Polygon":
        return float(0.0 if geom.is_empty else _polygon_area_m2(geom))

    if geom_type == "MultiPolygon":
        return float(sum(_polygon_area_m2(part) for part in geom.geoms if not part.is_empty))

    raise TypeError(f"Expected a Polygon or MultiPolygon, got {geom_type or type(geom).__name__}")