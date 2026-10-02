```python
"""
Module for computing geodesic area of Shapely geometries in square meters.
"""

from pyproj import Geod
from shapely.geometry import Polygon, MultiPolygon

# WGS84 ellipsoid
_GEOD = Geod(ellps="WGS84")


def area_m2(geom: Polygon | MultiPolygon) -> float:
    """
    Return the area of a Polygon or MultiPolygon in square meters.

    The input geometry must have coordinates in EPSG:4326 (longitude/latitude).
    The calculation uses geodesic algorithms on the WGS84 ellipsoid and is
    accurate for polygons anywhere on Earth.

    Parameters
    ----------
    geom : shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        Geometry in WGS84 (EPSG:4326).

    Returns
    -------
    float
        Area in square meters.
    """
    # pyproj's geometry_area_perimeter returns signed area (positive for
    # counter‑clockwise exterior rings). For valid polygons the sum is positive.
    # We take the absolute value to guard against unexpected ring orientations.
    area, _ = _GEOD.geometry_area_perimeter(geom)
    return abs(area)
```