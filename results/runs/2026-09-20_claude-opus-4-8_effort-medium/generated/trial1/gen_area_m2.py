"""Compute geodesic areas of WGS84 (EPSG:4326) polygons in square meters."""

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon

# WGS84 ellipsoid; used for geodesic area computation accurate worldwide.
_GEOD = Geod(ellps="WGS84")


def _polygon_area_m2(poly):
    """Return the absolute geodesic area of a single Polygon, minus its holes."""
    # geometry_area_perimeter returns a signed area (sign depends on ring
    # orientation); take the absolute value. Exterior area minus interior holes.
    exterior_area = abs(_GEOD.geometry_area_perimeter(poly.exterior)[0])
    holes_area = sum(
        abs(_GEOD.geometry_area_perimeter(ring)[0]) for ring in poly.interiors
    )
    return exterior_area - holes_area


def area_m2(geom):
    """Area in square meters of a WGS84 (lon/lat) Polygon or MultiPolygon.

    Uses geodesic computation on the WGS84 ellipsoid, so results are accurate
    for polygons anywhere on Earth.
    """
    if isinstance(geom, Polygon):
        return float(_polygon_area_m2(geom))
    if isinstance(geom, MultiPolygon):
        return float(sum(_polygon_area_m2(poly) for poly in geom.geoms))
    raise TypeError(f"Expected Polygon or MultiPolygon, got {type(geom).__name__}")