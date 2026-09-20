```python
"""Geodesic area of EPSG:4326 (lon/lat) polygons in square metres.

Uses Karney's geodesic algorithms on the WGS84 ellipsoid via pyproj, so the
result is accurate for any polygon on Earth, including ones that straddle
the antimeridian or enclose a pole (as long as the ring is a valid, closed
sequence of lon/lat vertices connected by geodesics).
"""

from __future__ import annotations

from typing import Union

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

__all__ = ["area_m2"]

_WGS84 = Geod(ellps="WGS84")


def _ring_area(coords) -> float:
    """Unsigned geodesic area of a single closed lon/lat ring."""
    lons = [float(c[0]) for c in coords]
    lats = [float(c[1]) for c in coords]
    if len(lons) < 3:
        return 0.0
    area, _perimeter = _WGS84.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    area = _ring_area(poly.exterior.coords)
    for interior in poly.interiors:
        area -= _ring_area(interior.coords)
    return max(area, 0.0)


def area_m2(geom: Union[Polygon, MultiPolygon]) -> float:
    """Return the area of ``geom`` in square metres.

    Parameters
    ----------
    geom
        A shapely ``Polygon`` or ``MultiPolygon`` whose coordinates are
        longitude/latitude degrees in EPSG:4326 (WGS84).

    Returns
    -------
    float
        Geodesic area on the WGS84 ellipsoid, in square metres. Holes are
        subtracted; multipolygon parts are summed. Empty geometries give 0.0.
    """
    if geom is None:
        raise TypeError("geom must be a shapely Polygon or MultiPolygon, not None")

    if isinstance(geom, Polygon):
        return float(_polygon_area(geom))

    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(p) for p in geom.geoms))

    raise TypeError(
        f"geom must be a shapely Polygon or MultiPolygon, got {type(geom).__name__}"
    )
```