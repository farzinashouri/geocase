```python
"""Geodesic area of WGS84 (EPSG:4326) polygons.

``area_m2`` computes the true area on the WGS84 ellipsoid using geodesic
polygon integration (pyproj/GeographicLib), so it stays accurate at any
latitude and for polygons of any size, unlike a planar computation in
degrees or a single fixed projected CRS.

Notes
-----
* Edges are treated as geodesics between consecutive vertices, which is
  the usual interpretation of a lon/lat ring and handles antimeridian
  crossings (e.g. 179 -> -179) without special casing.
* Interior rings (holes) are subtracted; ring winding order is ignored.
* GeographicLib reduces a ring's signed area modulo the total area of the
  ellipsoid, so a single ring enclosing more than half the globe is
  reported as its complement. That case is inherently ambiguous for a
  lon/lat ring and is not disambiguated here.
"""

from __future__ import annotations

import numpy as np
from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

__all__ = ["area_m2"]

# Pure in-memory ellipsoid definition; constructing it touches no I/O.
_GEOD = Geod(ellps="WGS84")


def _ring_area_m2(ring) -> float:
    """Unsigned geodesic area enclosed by a single linear ring."""
    coords = np.asarray(ring.coords, dtype=float)
    if coords.shape[0] < 3:
        return 0.0
    # Ignore any z (or m) values that may be present.
    area, _perimeter = _GEOD.polygon_area_perimeter(coords[:, 0], coords[:, 1])
    return abs(area)


def _polygon_area_m2(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    area = _ring_area_m2(poly.exterior)
    for hole in poly.interiors:
        area -= _ring_area_m2(hole)
    # Guards against malformed input whose holes are not inside the shell.
    return max(area, 0.0)


def area_m2(geom) -> float:
    """Return the area of a lon/lat ``Polygon``/``MultiPolygon`` in m².

    Parameters
    ----------
    geom
        A shapely ``Polygon`` or ``MultiPolygon`` with coordinates in
        EPSG:4326 (x = longitude, y = latitude, both in degrees).

    Returns
    -------
    float
        Area in square meters on the WGS84 ellipsoid. Empty geometries
        give ``0.0``.

    Raises
    ------
    TypeError
        If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(part) for part in geom.geoms))
    raise TypeError(
        "area_m2() expects a shapely Polygon or MultiPolygon, got "
        f"{type(geom).__name__}"
    )
```