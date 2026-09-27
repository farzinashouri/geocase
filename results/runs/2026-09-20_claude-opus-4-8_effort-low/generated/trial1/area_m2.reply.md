```python
"""Compute geodesic area of WGS84 lon/lat polygons in square meters."""

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

_GEOD = Geod(ellps="WGS84")


def _polygon_area_m2(poly: Polygon) -> float:
    """Geodesic area of a single Polygon, subtracting holes."""
    if poly.is_empty:
        return 0.0
    lon, lat = poly.exterior.coords.xy
    area, _ = _GEOD.polygon_area_perimeter(lon, lat)
    total = abs(area)
    for ring in poly.interiors:
        ilon, ilat = ring.coords.xy
        hole_area, _ = _GEOD.polygon_area_perimeter(ilon, ilat)
        total -= abs(hole_area)
    return total


def area_m2(geom) -> float:
    """Return the geodesic area in square meters of a shapely Polygon or
    MultiPolygon whose coordinates are longitude/latitude in EPSG:4326.

    Uses pyproj's geodesic area computation on the WGS84 ellipsoid, so results
    are accurate for polygons anywhere on Earth.
    """
    if geom is None or geom.is_empty:
        return 0.0

    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))

    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(p) for p in geom.geoms))

    raise TypeError(f"Expected Polygon or MultiPolygon, got {type(geom).__name__}")
```