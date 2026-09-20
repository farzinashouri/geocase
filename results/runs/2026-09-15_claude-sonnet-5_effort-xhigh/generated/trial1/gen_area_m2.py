"""Geodesic area computation for WGS84 (EPSG:4326) polygons."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Union

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon


@lru_cache(maxsize=1)
def _geod() -> Geod:
    return Geod(ellps="WGS84")


def _ring_area(coords: Iterable[tuple]) -> float:
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    area, _perimeter = _geod().polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(polygon: Polygon) -> float:
    area = _ring_area(polygon.exterior.coords)
    for interior in polygon.interiors:
        area -= _ring_area(interior.coords)
    return area


def area_m2(geom: Union[Polygon, MultiPolygon]) -> float:
    """Return the geodesic area (m^2) of a lon/lat Polygon or MultiPolygon.

    Uses ellipsoidal (WGS84) geodesic integration, so results are accurate
    for polygons anywhere on Earth, including near the poles and for very
    large or very small features. Polygon holes are subtracted regardless
    of ring winding order.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(poly) for poly in geom.geoms))
    raise TypeError(f"Unsupported geometry type: {geom.geom_type!r}")