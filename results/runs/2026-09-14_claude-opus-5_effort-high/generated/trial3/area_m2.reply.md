```python
"""Geodesic area of EPSG:4326 (WGS84 lon/lat) polygons, in square meters.

Areas are computed on the WGS84 ellipsoid with ``pyproj.Geod`` (geographiclib's
exact polygon-area algorithm), so results are accurate anywhere on Earth,
including polygons that cross the antimeridian or enclose a pole, without
picking a local projection.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import shapely
from pyproj import Geod
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """WGS84 ellipsoid, built on first use so importing this module is inert."""
    return Geod(ellps="WGS84")


def _ring_area_m2(ring) -> float:
    """Unsigned geodesic area enclosed by a single LinearRing."""
    if ring is None or ring.is_empty:
        return 0.0

    coords = shapely.get_coordinates(ring)  # drops any Z, keeps lon/lat order
    if len(coords) > 1 and np.array_equal(coords[0], coords[-1]):
        coords = coords[:-1]  # geographiclib closes the ring implicitly
    if len(coords) < 3:
        return 0.0

    # Sign depends on ring orientation, which we do not rely on.
    area, _perimeter = _geod().polygon_area_perimeter(coords[:, 0], coords[:, 1])
    return abs(area)


def _polygon_area_m2(polygon) -> float:
    area = _ring_area_m2(polygon.exterior)
    for interior in polygon.interiors:
        area -= _ring_area_m2(interior)
    return area


def area_m2(geom: BaseGeometry) -> float:
    """Return the area of a WGS84 lon/lat Polygon or MultiPolygon, in m².

    Args:
        geom: A shapely ``Polygon`` or ``MultiPolygon`` with coordinates in
            EPSG:4326 (longitude, latitude in degrees).

    Returns:
        The ellipsoidal area in square meters. Empty geometries give ``0.0``.

    Raises:
        TypeError: If ``geom`` is not a Polygon or MultiPolygon.
    """
    geom_type = getattr(geom, "geom_type", None)

    if geom_type == "Polygon":
        parts = (geom,)
    elif geom_type == "MultiPolygon":
        parts = geom.geoms
    else:
        raise TypeError(
            f"area_m2 expects a Polygon or MultiPolygon, got {type(geom).__name__}"
        )

    if geom.is_empty:
        return 0.0

    # Sum parts individually so that differing ring orientations cannot cancel.
    total = sum(_polygon_area_m2(part) for part in parts)

    # Holes larger than their shell mean an invalid input; clamp instead of
    # returning a negative area.
    return float(max(total, 0.0))
```