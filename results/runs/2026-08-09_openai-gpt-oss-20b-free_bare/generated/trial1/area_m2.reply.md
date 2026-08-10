```python
"""
area_m2.py

Provides a single function `area_m2(geom)` that returns the area of a
Shapely `Polygon` or `MultiPolygon` (in EPSG:4326) in square metres.
"""

from __future__ import annotations

from shapely.geometry import Polygon, MultiPolygon
from pyproj import Geod

# WGS84 ellipsoid is the default for Geod, but we set it explicitly for clarity.
_geod = Geod(ellps="WGS84")


def _polygon_area(poly: Polygon) -> float:
    """
    Compute the area of a single Shapely Polygon in square metres.
    Handles exterior ring and any interior rings (holes).
    """
    if poly.is_empty:
        return 0.0

    # Exterior ring
    ex_lons, ex_lats = zip(*poly.exterior.coords)
    area, _ = _geod.polygon_area_perimeter(ex_lons, ex_lats)
    area = abs(area)

    # Subtract holes
    for interior in poly.interiors:
        in_lons, in_lats = zip(*interior.coords)
        hole_area, _ = _geod.polygon_area_perimeter(in_lons, in_lats)
        area -= abs(hole_area)

    return area


def area_m2(geom: Polygon | MultiPolygon) -> float:
    """
    Return the area of a Shapely Polygon or MultiPolygon in square metres.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry with coordinates in EPSG:4326 (longitude/latitude).

    Returns
    -------
    float
        Area in square metres. Returns 0.0 for empty geometries.

    Raises
    ------
    TypeError
        If the geometry is not a Polygon or MultiPolygon.
    """
    if geom is None:
        return 0.0

    if isinstance(geom, Polygon):
        return _polygon_area(geom)

    if isinstance(geom, MultiPolygon):
        total = 0.0
        for poly in geom.geoms:
            total += _polygon_area(poly)
        return total

    raise TypeError(
        f"Unsupported geometry type {type(geom).__name__}. "
        "Expected shapely.geometry.Polygon or MultiPolygon."
    )
```