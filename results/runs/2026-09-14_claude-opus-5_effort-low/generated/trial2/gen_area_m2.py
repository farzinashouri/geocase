"""Geodesic area of WGS84 (EPSG:4326) polygons, in square meters."""

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

_GEOD = Geod(ellps="WGS84")


def _ring_area(ring) -> float:
    """Unsigned geodesic area enclosed by a single linear ring, in m^2."""
    lons, lats = zip(*ring.coords)
    area, _perimeter = _GEOD.polygon_area_perimeter(lons, lats)
    return abs(area)


def _polygon_area(poly: Polygon) -> float:
    if poly.is_empty:
        return 0.0
    area = _ring_area(poly.exterior)
    for hole in poly.interiors:
        area -= _ring_area(hole)
    return area


def area_m2(geom) -> float:
    """Return the geodesic area of a lon/lat Polygon or MultiPolygon in m^2.

    Coordinates are interpreted as longitude/latitude degrees on the WGS84
    ellipsoid, so the result is accurate for polygons anywhere on Earth.
    Interior rings (holes) are subtracted.
    """
    if geom is None or geom.is_empty:
        return 0.0

    if isinstance(geom, Polygon):
        return float(_polygon_area(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area(p) for p in geom.geoms))

    raise TypeError(f"expected Polygon or MultiPolygon, got {type(geom).__name__}")