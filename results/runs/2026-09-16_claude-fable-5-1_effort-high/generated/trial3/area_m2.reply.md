One-line plan: I'll compute the area geodesically on the WGS84 ellipsoid with pyproj's `Geod`, ring by ring, so orientation and holes are handled robustly and no projection distortion is involved.

```python
"""Geodesic area of EPSG:4326 (lon/lat) polygons on the WGS84 ellipsoid.

The area is computed with Karney's geodesic polygon algorithm (via
``pyproj.Geod``), so it is accurate anywhere on Earth, including near the
poles and across the antimeridian, without choosing a local projection.
Polygon edges are treated as geodesics between consecutive vertices.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

__all__ = ["area_m2"]


@lru_cache(maxsize=1)
def _wgs84_geod() -> Geod:
    """Lazily build the WGS84 ellipsoid model (avoids import-time work)."""
    return Geod(ellps="WGS84")


def _ring_area_m2(coords: Iterable[tuple[float, ...]]) -> float:
    """Unsigned geodesic area (m^2) enclosed by one linear ring."""
    pts = list(coords)
    if len(pts) < 4:  # fewer than 3 distinct vertices: degenerate ring
        return 0.0
    lons = [float(p[0]) for p in pts]
    lats = [float(p[1]) for p in pts]
    area, _perimeter = _wgs84_geod().polygon_area_perimeter(lons, lats)
    # Sign only encodes ring orientation; magnitude is what we want.
    return abs(area)


def _polygon_area_m2(poly: Polygon) -> float:
    """Geodesic area of one polygon: exterior minus its holes."""
    if poly.is_empty:
        return 0.0
    area = _ring_area_m2(poly.exterior.coords)
    for hole in poly.interiors:
        area -= _ring_area_m2(hole.coords)
    return max(area, 0.0)


def area_m2(geom: BaseGeometry) -> float:
    """Return the area in square meters of a lon/lat (EPSG:4326) polygon.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry whose coordinates are (longitude, latitude) in degrees on
        WGS84. Interior rings (holes) are subtracted; ring orientation does
        not matter.

    Returns
    -------
    float
        Geodesic area on the WGS84 ellipsoid, in square meters. Empty
        geometries yield 0.0.

    Raises
    ------
    TypeError
        If ``geom`` is not a Polygon or MultiPolygon.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(p) for p in geom.geoms))
    raise TypeError(
        "area_m2 expects a shapely Polygon or MultiPolygon, "
        f"got {type(geom).__name__}"
    )
```