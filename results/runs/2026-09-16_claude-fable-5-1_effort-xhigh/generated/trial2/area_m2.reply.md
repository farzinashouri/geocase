```python
"""Ellipsoidal (geodesic) area of longitude/latitude polygons.

This module exposes a single function, :func:`area_m2`, which returns the
surface area in square metres of a shapely ``Polygon`` or ``MultiPolygon``
whose coordinates are geographic longitude/latitude on WGS84 (EPSG:4326).

The area is computed directly on the WGS84 ellipsoid with GeographicLib's
polygon-area algorithm, as exposed by :class:`pyproj.Geod`.  No map
projection is involved, so the result does not degrade with latitude or with
polygon size, and it is correct for polygons that straddle the antimeridian
or enclose a pole.

Conventions
-----------
* Edges are interpreted as geodesics between consecutive vertices (the usual
  convention, shared with e.g. PostGIS ``geography`` and GeographicLib).
* Ring orientation does not matter: the exterior ring always contributes a
  positive area and interior rings (holes) are always subtracted.
* Z/M coordinates, if present, are ignored.
* Empty geometries have an area of ``0.0``.

Importing this module has no side effects; the ellipsoid model is built
lazily on first use.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np
import shapely
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]


@lru_cache(maxsize=None)
def _wgs84() -> Geod:
    """Build (once) and return the WGS84 ellipsoid used for all computations."""
    return Geod(ellps="WGS84")


def _ring_area_m2(ring: Any, geod: Geod) -> float:
    """Unsigned geodesic area enclosed by one linear ring, in square metres."""
    coords = shapely.get_coordinates(ring)  # shape (n, 2); Z/M are dropped
    if coords.shape[0] < 3:
        return 0.0
    lons = np.ascontiguousarray(coords[:, 0], dtype=np.float64)
    lats = np.ascontiguousarray(coords[:, 1], dtype=np.float64)
    signed_area, _perimeter = geod.polygon_area_perimeter(lons, lats)
    # The sign only encodes traversal direction (CCW positive); drop it so the
    # caller can treat exterior rings and holes uniformly.
    return abs(float(signed_area))


def _polygon_area_m2(polygon: Polygon, geod: Geod) -> float:
    """Geodesic area of a single polygon: exterior ring minus all holes."""
    if polygon.is_empty:
        return 0.0
    area = _ring_area_m2(polygon.exterior, geod)
    for hole in polygon.interiors:
        area -= _ring_area_m2(hole, geod)
    # Guard against tiny negative round-off when holes fill the exterior.
    return max(area, 0.0)


def _geometry_area_m2(geom: BaseGeometry, geod: Geod) -> float:
    """Dispatch on geometry type; multi-part geometries are summed."""
    if geom.is_empty:
        return 0.0
    if isinstance(geom, Polygon):
        return _polygon_area_m2(geom, geod)
    if isinstance(geom, MultiPolygon):
        return sum(_polygon_area_m2(part, geod) for part in geom.geoms)
    if hasattr(geom, "geoms"):
        # GeometryCollection: fine as long as every member is polygonal.
        return sum(_geometry_area_m2(part, geod) for part in geom.geoms)
    raise TypeError(
        "area_m2() expects a Polygon or MultiPolygon, "
        f"got {geom.geom_type}"
    )


def area_m2(geom: Polygon | MultiPolygon) -> float:
    """Return the area of ``geom`` in square metres on the WGS84 ellipsoid.

    Parameters
    ----------
    geom
        A shapely ``Polygon`` or ``MultiPolygon`` whose coordinates are
        longitude/latitude degrees in EPSG:4326.  GeoJSON-like mappings and
        objects exposing ``__geo_interface__`` are accepted as well.

    Returns
    -------
    float
        Geodesic surface area in square metres.  Always non-negative,
        independent of ring orientation, with holes subtracted.  Empty
        geometries yield ``0.0``.

    Raises
    ------
    TypeError
        If ``geom`` is not (convertible to) a polygonal shapely geometry.

    Examples
    --------
    >>> from shapely.geometry import box
    >>> round(area_m2(box(0, 0, 1, 1)) / 1e6, 1)   # 1x1 degree cell at the equator, km²
    12308.8
    """
    if not isinstance(geom, BaseGeometry):
        try:
            geom = shape(geom)
        except Exception as exc:  # noqa: BLE001 - re-raised as a TypeError
            raise TypeError(
                "area_m2() expects a shapely Polygon or MultiPolygon, "
                f"got {type(geom).__name__}"
            ) from exc
    return float(_geometry_area_m2(geom, _wgs84()))
```