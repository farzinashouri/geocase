```python
"""Geodesic area of EPSG:4326 (WGS84 lon/lat) polygons in square meters.

The area is computed on the WGS84 ellipsoid with pyproj's Geod (Karney's
geodesic algorithms), so results are accurate anywhere on Earth, including
polygons that straddle the antimeridian or enclose a pole. Holes are
subtracted from their parent polygon.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable

import numpy as np
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    # Created lazily so importing the module has no side effects.
    return Geod(ellps="WGS84")


def _ring_area(coords: Iterable) -> float:
    """Unsigned geodesic area (m^2) enclosed by a ring of lon/lat vertices."""
    arr = np.asarray(list(coords), dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 3:
        return 0.0
    lons = arr[:, 0]
    lats = arr[:, 1]
    area, _perimeter = _geod().polygon_area_perimeter(lons, lats)
    return abs(float(area))


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    area = _ring_area(poly.exterior.coords)
    for hole in poly.interiors:
        area -= _ring_area(hole.coords)
    return max(area, 0.0)


def area_m2(geom: BaseGeometry) -> float:
    """Return the area in square meters of a WGS84 Polygon or MultiPolygon.

    Parameters
    ----------
    geom
        A shapely ``Polygon`` or ``MultiPolygon`` whose coordinates are
        longitude/latitude degrees in EPSG:4326.

    Returns
    -------
    float
        Geodesic area on the WGS84 ellipsoid, in square meters.
    """
    if geom is None or geom.is_empty:
        return 0.0
    if isinstance(geom, Polygon):
        return _polygon_area(geom)
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(p) for p in geom.geoms))
    raise TypeError(
        f"area_m2 expects a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
    )
```