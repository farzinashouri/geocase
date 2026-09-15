```python
"""Geodesic area of EPSG:4326 (WGS84 lon/lat) polygons, in square meters.

Areas are computed directly on the WGS84 ellipsoid with GeographicLib (via
pyproj), so there is no projection to pick and no distortion that grows with
latitude or polygon size. Edges are treated as geodesics between consecutive
vertices, which also makes antimeridian-crossing and pole-enclosing rings work
without special casing, as long as consecutive vertices are less than 180
degrees apart in longitude.

Ring orientation is ignored: each ring contributes its unsigned area, and
interior rings are subtracted from the exterior. The one case this cannot
resolve is a ring enclosing more than half the globe, which is
indistinguishable from its complement without trusting orientation; such a ring
reports the area of the smaller region.
"""

from __future__ import annotations

import numpy as np
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

__all__ = ["area_m2"]

_GEOD = Geod(ellps="WGS84")


def _ring_area_m2(ring) -> float:
    """Unsigned geodesic area enclosed by one linear ring, in square meters."""
    coords = np.asarray(ring.coords, dtype=float)
    if coords.shape[0] < 3:
        return 0.0
    # The repeated closing vertex is harmless: it adds a zero-length edge.
    area, _perimeter = _GEOD.polygon_area_perimeter(coords[:, 0], coords[:, 1])
    return abs(area)


def _polygon_area_m2(polygon: Polygon) -> float:
    area = _ring_area_m2(polygon.exterior)
    for interior in polygon.interiors:
        area -= _ring_area_m2(interior)
    return max(area, 0.0)


def area_m2(geom) -> float:
    """Return the geodesic area of a WGS84 lon/lat polygon in square meters.

    Parameters
    ----------
    geom:
        A shapely ``Polygon`` or ``MultiPolygon`` whose coordinates are
        (longitude, latitude) in degrees, EPSG:4326. Z values, if present, are
        ignored. Empty geometries return ``0.0``.

    Raises
    ------
    TypeError:
        If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(part) for part in geom.geoms))
    raise TypeError(
        f"expected a Polygon or MultiPolygon, got {type(geom).__name__}"
    )
```