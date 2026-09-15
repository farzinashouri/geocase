```python
"""Geodesic area of EPSG:4326 (WGS84 lon/lat) polygons, in square meters.

Areas are computed on the WGS84 ellipsoid with pyproj's geodesic polygon
routines (GeographicLib), so accuracy does not depend on where the polygon
sits or on picking a local projection. Polygon edges are treated as geodesics
between consecutive vertices; longitude differences use the shortest arc, so
rings that cross the antimeridian need no special handling.

Limitation: a ring encloses two complementary regions on the sphere, and ring
orientation is unreliable in practice (and ill-defined for polygons containing
a pole), so the smaller of the two is always returned. Inputs describing a
region larger than half the Earth would yield the complement instead.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

__all__ = ["area_m2"]

_ELLIPSOID = "WGS84"

# Built on first use so that importing this module does no work.
_GEOD: Geod | None = None


def _geod() -> Geod:
    global _GEOD
    if _GEOD is None:
        _GEOD = Geod(ellps=_ELLIPSOID)
    return _GEOD


def _ring_area_m2(coords: Iterable[Sequence[float]]) -> float:
    """Unsigned geodesic area enclosed by a single linear ring."""
    lons: list[float] = []
    lats: list[float] = []
    for point in coords:
        lons.append(point[0])
        lats.append(point[1])

    # Fewer than three vertices encloses nothing. Shapely repeats the first
    # vertex to close the ring; the geodesic routine closes it itself, and the
    # duplicate is harmless.
    if len(lons) < 3:
        return 0.0

    area, _perimeter = _geod().polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area_m2(polygon: Polygon) -> float:
    if polygon.is_empty:
        return 0.0
    area = _ring_area_m2(polygon.exterior.coords)
    for hole in polygon.interiors:
        area -= _ring_area_m2(hole.coords)
    # Holes are assumed to lie inside the shell; clamp so numerical noise or a
    # malformed ring cannot produce a negative area.
    return max(area, 0.0)


def area_m2(geom: Polygon | MultiPolygon) -> float:
    """Return the area of a lon/lat (EPSG:4326) polygon in square meters.

    Args:
        geom: A shapely ``Polygon`` or ``MultiPolygon`` with coordinates in
            degrees of longitude and latitude on WGS84.

    Returns:
        The ellipsoidal area in square meters, with interior rings (holes)
        subtracted. Empty geometries return ``0.0``.

    Raises:
        TypeError: If ``geom`` is not a ``Polygon`` or ``MultiPolygon``.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(part) for part in geom.geoms))
    raise TypeError(
        f"expected a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
    )
```