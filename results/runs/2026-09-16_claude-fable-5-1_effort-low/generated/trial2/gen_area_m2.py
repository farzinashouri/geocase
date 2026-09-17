"""Geodesic area of EPSG:4326 (lon/lat) polygons in square meters."""

from __future__ import annotations

from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

_WGS84_A = 6378137.0
_WGS84_F = 1.0 / 298.257223563

_geod = None  # lazily constructed so importing has no side effects beyond module load


def _get_geod():
    global _geod
    if _geod is None:
        from pyproj import Geod

        _geod = Geod(a=_WGS84_A, f=_WGS84_F)
    return _geod


def _ring_area(geod, ring) -> float:
    coords = list(ring.coords)
    if len(coords) < 4:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    area, _perimeter = geod.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(geod, poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    outer = _ring_area(geod, poly.exterior)
    holes = sum(_ring_area(geod, r) for r in poly.interiors)
    return max(outer - holes, 0.0)


def area_m2(geom: BaseGeometry) -> float:
    """Return the geodesic area in square meters of a WGS84 Polygon/MultiPolygon.

    Uses Karney's geodesic algorithms on the WGS84 ellipsoid (via pyproj.Geod),
    so results are accurate anywhere on Earth, including polygons spanning
    the poles or the antimeridian, provided rings are given as ordinary
    lon/lat vertex sequences. Holes are subtracted from their enclosing
    exterior ring.
    """
    if geom is None or geom.is_empty:
        return 0.0
    geod = _get_geod()
    if isinstance(geom, Polygon):
        return float(_polygon_area(geod, geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(geod, p) for p in geom.geoms))
    raise TypeError(
        f"area_m2 expects a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
    )