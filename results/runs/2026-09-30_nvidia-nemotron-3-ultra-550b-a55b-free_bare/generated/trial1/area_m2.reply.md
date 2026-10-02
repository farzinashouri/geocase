```python
"""
Module for calculating the geodetic area of Shapely polygons in square meters.
"""

import pyproj
from shapely.geometry import Polygon, MultiPolygon


def area_m2(geom) -> float:
    """
    Calculate the area of a Polygon or MultiPolygon in square meters.

    The input geometry must have coordinates in EPSG:4326 (longitude/latitude, WGS84).
    The calculation uses a geodetic algorithm (pyproj.Geod) for high accuracy
    anywhere on Earth.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        The geometry to measure.

    Returns
    -------
    float
        Area in square meters. Returns 0.0 for empty geometries.

    Raises
    ------
    TypeError
        If `geom` is not a Polygon or MultiPolygon.
    """
    if geom.is_empty:
        return 0.0

    geod = pyproj.Geod(ellps="WGS84")

    if isinstance(geom, Polygon):
        area, _ = geod.geometry_area_perimeter(geom)
        return abs(area)

    if isinstance(geom, MultiPolygon):
        total = 0.0
        for polygon in geom.geoms:
            area, _ = geod.geometry_area_perimeter(polygon)
            total += abs(area)
        return total

    raise TypeError("geom must be a shapely Polygon or MultiPolygon")
```