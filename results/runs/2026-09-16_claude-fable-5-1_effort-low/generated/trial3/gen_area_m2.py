"""Geodesic area of EPSG:4326 (WGS84) polygons in square meters.

The area is computed on the WGS84 ellipsoid using pyproj's Geod, which
handles polygons anywhere on Earth, including those crossing the
antimeridian or enclosing a pole, without any projection step.
"""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]

_WGS84_GEOD = Geod(ellps="WGS84")


def _ring_area(coords) -> float:
    """Unsigned geodesic area (m^2) of a closed lon/lat ring."""
    lons = [float(c[0]) for c in coords]
    lats = [float(c[1]) for c in coords]
    if len(lons) < 3:
        return 0.0
    area, _perimeter = _WGS84_GEOD.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    exterior = _ring_area(poly.exterior.coords)
    holes = sum(_ring_area(ring.coords) for ring in poly.interiors)
    return max(exterior - holes, 0.0)


def area_m2(geom: BaseGeometry) -> float:
    """Return the geodesic area in square meters of a WGS84 Polygon/MultiPolygon.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry with (longitude, latitude) coordinates in EPSG:4326.

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