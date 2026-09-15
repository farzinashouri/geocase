"""Geodesic area of WGS84 (EPSG:4326) polygons, in square meters.

Areas are computed on the WGS84 ellipsoid with pyproj's geodesic routines
rather than by projecting, so results stay accurate for polygons anywhere
on Earth, including near the poles and for very large extents.
"""

from __future__ import annotations

import math
from functools import lru_cache

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    return Geod(ellps="WGS84")


@lru_cache(maxsize=1)
def _ellipsoid_area_m2() -> float:
    """Total surface area of the WGS84 ellipsoid."""
    g = _geod()
    a = g.a
    b = g.b
    if a == b:
        return 4.0 * math.pi * a * a
    e = math.sqrt(1.0 - (b * b) / (a * a))
    return 2.0 * math.pi * a * a * (1.0 + ((1.0 - e * e) / e) * math.atanh(e))


def _ring_area_m2(coords) -> float:
    """Unsigned geodesic area enclosed by a closed ring of (lon, lat) pairs."""
    pts = list(coords)
    if len(pts) < 4:  # fewer than 3 distinct vertices encloses nothing
        return 0.0
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    area, _perimeter = _geod().polygon_area_perimeter(lons, lats)
    area = abs(area)
    # A ring wound the "wrong" way reports the complement of its own area;
    # a valid ring is whichever of the two interpretations is smaller.
    total = _ellipsoid_area_m2()
    return min(area, total - area)


def _polygon_area_m2(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    area = _ring_area_m2(poly.exterior.coords)
    for interior in poly.interiors:
        area -= _ring_area_m2(interior.coords)
    return max(area, 0.0)


def area_m2(geom) -> float:
    """Return the geodesic area of a lon/lat Polygon or MultiPolygon, in m^2.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry whose coordinates are longitude/latitude degrees in
        EPSG:4326 (WGS84).

    Returns
    -------
    float
        Area in square meters (always non-negative). Empty geometries
        return 0.0.
    """
    if geom is None or geom.is_empty:
        return 0.0
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(p) for p in geom.geoms))
    raise TypeError(
        f"area_m2 expects a Polygon or MultiPolygon, got {type(geom).__name__}"
    )