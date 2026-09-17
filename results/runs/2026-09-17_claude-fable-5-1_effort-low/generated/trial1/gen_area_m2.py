"""Geodesic area of EPSG:4326 (lon/lat) polygons in square meters."""

from __future__ import annotations

from shapely.geometry import MultiPolygon, Polygon

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def _ring_area(coords) -> float:
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    area, _ = _GEOD.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    area = _ring_area(poly.exterior.coords)
    for interior in poly.interiors:
        area -= _ring_area(interior.coords)
    return max(area, 0.0)


def area_m2(geom) -> float:
    """Return the geodesic area in square meters of a Polygon or MultiPolygon
    with WGS84 longitude/latitude coordinates."""
    if geom is None or geom.is_empty:
        return 0.0
    if isinstance(geom, Polygon):
        return float(_polygon_area(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(p) for p in geom.geoms))
    raise TypeError(f"Expected Polygon or MultiPolygon, got {type(geom).__name__}")