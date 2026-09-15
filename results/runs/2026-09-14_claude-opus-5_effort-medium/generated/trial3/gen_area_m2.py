"""Geodesic area of WGS84 (EPSG:4326) polygons, in square meters.

Uses pyproj's GeographicLib bindings, which compute the area on the WGS84
ellipsoid directly from lon/lat vertices. This is accurate anywhere on Earth
(no projection choice, no zone boundaries, no distortion away from a central
meridian), and edges are treated as geodesics between consecutive vertices.

Importing this module has no side effects: the ``Geod`` instance is created
lazily on first use and cached.
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import Geod
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """Return a cached WGS84 geodesic calculator."""
    return Geod(ellps="WGS84")


def _ring_area_m2(coords) -> float:
    """Unsigned geodesic area enclosed by a closed ring of (lon, lat) pairs."""
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    if len(lons) < 3:
        return 0.0
    area, _perimeter = _geod().polygon_area_perimeter(lons, lats)
    # The sign only encodes ring orientation; magnitude is the enclosed area.
    return abs(area)


def _polygon_area_m2(polygon) -> float:
    if polygon.is_empty:
        return 0.0
    area = _ring_area_m2(polygon.exterior.coords)
    for interior in polygon.interiors:
        area -= _ring_area_m2(interior.coords)
    return area


def area_m2(geom: BaseGeometry) -> float:
    """Area of a lon/lat (EPSG:4326) polygonal geometry in square meters.

    Parameters
    ----------
    geom:
        A shapely ``Polygon`` or ``MultiPolygon`` with coordinates ordered
        (longitude, latitude) in degrees on WGS84. Holes are subtracted from
        their enclosing shell.

    Returns
    -------
    float
        Non-negative area in square meters. Empty geometries give ``0.0``.

    Raises
    ------
    TypeError
        If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    """
    geom_type = getattr(geom, "geom_type", None)

    if geom_type == "Polygon":
        return float(_polygon_area_m2(geom))

    if geom_type == "MultiPolygon":
        return float(sum(_polygon_area_m2(part) for part in geom.geoms))

    raise TypeError(
        "area_m2() expects a shapely Polygon or MultiPolygon, got "
        f"{geom_type or type(geom).__name__!r}"
    )