"""Geodesic area of WGS84 lon/lat polygons.

Computes the area of a shapely Polygon or MultiPolygon whose coordinates are
longitude/latitude (EPSG:4326) on the WGS84 ellipsoid, using pyproj's
geodesic (Karney) algorithms. This is accurate anywhere on Earth, including
polygons that cross the antimeridian or contain a pole, and correctly
subtracts interior rings (holes).
"""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]

_WGS84 = Geod(ellps="WGS84")


def _ring_area(coords) -> float:
    """Unsigned geodesic area (m²) of a single closed ring given lon/lat coords."""
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    if len(lons) < 3:
        return 0.0
    area, _perimeter = _WGS84.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    area = _ring_area(poly.exterior.coords)
    for interior in poly.interiors:
        area -= _ring_area(interior.coords)
    return max(area, 0.0)


def area_m2(geom: BaseGeometry) -> float:
    """Return the geodesic area in square meters of a WGS84 Polygon/MultiPolygon.

    Parameters
    ----------
    geom
        A shapely ``Polygon`` or ``MultiPolygon`` with (lon, lat) coordinates
        in EPSG:4326. Holes are subtracted; multipolygon parts are summed.

    Returns
    -------
    float
        Area in square meters (always >= 0). Empty geometries return 0.0.

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