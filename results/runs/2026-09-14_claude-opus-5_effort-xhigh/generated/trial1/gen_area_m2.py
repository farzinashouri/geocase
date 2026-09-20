"""Geodesic area of WGS84 (EPSG:4326) polygons, in square meters.

``area_m2`` measures a shapely ``Polygon``/``MultiPolygon`` whose coordinates are
longitude/latitude degrees on the WGS84 ellipsoid.  The computation uses
GeographicLib's geodesic polygon algorithm (through :mod:`pyproj`), so it is
accurate anywhere on Earth without picking a per-geometry projection: no local
UTM/equal-area zone selection, no distortion blow-up near the poles, and edges
that cross the antimeridian are handled correctly because each edge is treated
as the shortest geodesic between its endpoints.

Caveat inherent to unsigned areas: a single ring enclosing more than half the
ellipsoid is indistinguishable from its complement traversed the other way, and
this module reports the smaller of the two.  Ordinary geometries -- including
whole continents and oceans -- are unaffected.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import shapely
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """WGS84 ellipsoid model, built on first use so importing stays inert."""
    return Geod(ellps="WGS84")


def _ring_area_m2(ring: shapely.LinearRing) -> float:
    """Unsigned geodesic area enclosed by one ring, in square meters."""
    coords = shapely.get_coordinates(ring)  # (N, 2), drops any Z
    if coords.shape[0] < 3:
        return 0.0
    if not np.isfinite(coords).all():
        raise ValueError("geometry contains non-finite coordinates")
    area, _perimeter = _geod().polygon_area_perimeter(coords[:, 0], coords[:, 1])
    # The returned area is signed by the ring's winding order; only the
    # magnitude of the enclosed region is meaningful here.
    return abs(area)


def _polygon_area_m2(polygon: Polygon) -> float:
    if polygon.is_empty:
        return 0.0
    area = _ring_area_m2(polygon.exterior)
    for interior in polygon.interiors:
        area -= _ring_area_m2(interior)
    # Holes that overlap or escape the shell (invalid input) could push the
    # total negative; clamp rather than hand back a nonsensical area.
    return max(area, 0.0)


def area_m2(geom: Polygon | MultiPolygon) -> float:
    """Return the area of ``geom`` in square meters.

    Parameters
    ----------
    geom:
        A shapely ``Polygon`` or ``MultiPolygon`` with longitude/latitude
        coordinates in EPSG:4326 (x = longitude, y = latitude, degrees).

    Returns
    -------
    float
        Area on the WGS84 ellipsoid in m^2, with interior rings (holes)
        subtracted.  Empty geometries measure ``0.0``.

    Raises
    ------
    TypeError
        If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    ValueError
        If any coordinate is NaN or infinite.
    """
    if isinstance(geom, Polygon):
        polygons: tuple[Polygon, ...] | object = (geom,)
    elif isinstance(geom, MultiPolygon):
        polygons = geom.geoms
    else:
        raise TypeError(
            "area_m2() expects a Polygon or MultiPolygon, got "
            f"{type(geom).__name__}"
        )
    return float(sum(_polygon_area_m2(polygon) for polygon in polygons))