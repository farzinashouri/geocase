"""Geodesic area computation for WGS84 polygons.

Provides :func:`area_m2`, which computes the area in square meters of a
shapely ``Polygon`` or ``MultiPolygon`` whose coordinates are
longitude/latitude in EPSG:4326, using geodesic math on the WGS84
ellipsoid (accurate anywhere on Earth, including polygons spanning the
antimeridian or poles, since the computation is done on the ellipsoid
itself rather than via a planar projection).
"""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient

__all__ = ["area_m2"]

_WGS84_GEOD = Geod(ellps="WGS84")


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    # Normalize ring orientation (exterior CCW, holes CW) so pyproj's
    # signed summation subtracts holes instead of adding them.
    area, _perimeter = _WGS84_GEOD.geometry_area_perimeter(orient(poly, sign=1.0))
    return abs(area)


def area_m2(geom: Polygon | MultiPolygon) -> float:
    """Return the area of *geom* in square meters.

    Parameters
    ----------
    geom:
        A shapely ``Polygon`` or ``MultiPolygon`` with coordinates in
        EPSG:4326 (longitude, latitude order).

    Returns
    -------
    float
        The geodesic area on the WGS84 ellipsoid, in square meters.
        Always non-negative regardless of ring orientation; interior
        rings (holes) are subtracted.

    Raises
    ------
    TypeError
        If *geom* is not a Polygon or MultiPolygon.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(p) for p in geom.geoms))
    raise TypeError(
        "area_m2 expects a shapely Polygon or MultiPolygon, "
        f"got {type(geom).__name__}"
    )
