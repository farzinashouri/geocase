```python
"""Geodesic area of WGS84 (EPSG:4326) polygons, in square meters.

``area_m2`` measures a shapely ``Polygon`` / ``MultiPolygon`` whose coordinates
are longitude/latitude degrees on the WGS84 ellipsoid. The computation is
geodesic (GeographicLib, via pyproj) rather than projected, so there is no
UTM-zone or equal-area-projection choice to get wrong: polygons at the poles,
straddling the antimeridian, or spanning many degrees are all handled with
sub-ppm accuracy for their given vertices.

Caveats worth knowing:

* Edges are treated as geodesics between consecutive vertices, which is the
  standard interpretation of an EPSG:4326 polygon. Long edges therefore do not
  follow parallels of latitude -- densify the ring first if you need that.
* A single ring is only distinguishable from its complement by winding order,
  and winding order is not reliable in real-world data, so each ring is taken
  to enclose the smaller of the two. Rings covering more than half the
  ellipsoid are consequently out of scope.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from pyproj import Geod
from shapely import get_coordinates
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """The WGS84 ellipsoid, built on first use so importing has no side effects."""
    return Geod(ellps="WGS84")


def _ring_area_m2(ring) -> float:
    """Unsigned geodesic area enclosed by one linear ring."""
    coords = get_coordinates(ring)
    # Shapely stores rings closed; geographiclib closes them itself, so the
    # repeated final vertex is redundant (harmless, but drop it to be explicit).
    if len(coords) > 1 and np.array_equal(coords[0], coords[-1]):
        coords = coords[:-1]
    if len(coords) < 3:
        return 0.0  # degenerate: a point or a line encloses nothing
    area, _perimeter = _geod().polygon_area_perimeter(coords[:, 0], coords[:, 1])
    # The sign carries winding order only, which we deliberately do not trust.
    return abs(area)


def _polygon_area_m2(polygon: Polygon) -> float:
    """Exterior area less the area of any holes."""
    if polygon.is_empty:
        return 0.0
    area = _ring_area_m2(polygon.exterior)
    for hole in polygon.interiors:
        area -= _ring_area_m2(hole)
    return area


def area_m2(geom: BaseGeometry) -> float:
    """Return the geodesic area of ``geom`` in square meters.

    Args:
        geom: A shapely ``Polygon`` or ``MultiPolygon`` in EPSG:4326, i.e. with
            ``(longitude, latitude)`` coordinates in degrees. Holes are
            subtracted; empty geometries measure ``0.0``.

    Raises:
        TypeError: If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(part) for part in geom.geoms))
    raise TypeError(
        f"area_m2 expects a Polygon or MultiPolygon, got {type(geom).__name__}"
    )
```