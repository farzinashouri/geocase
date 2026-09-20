"""Geodesic length of a WGS84 LineString in meters."""

from pyproj import Geod
from shapely.geometry import LineString

_WGS84 = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length in meters of a LineString with EPSG:4326 (lon/lat) coordinates.

    Uses Karney's geodesic algorithms on the WGS84 ellipsoid via pyproj, so the
    result is accurate (sub-millimeter) anywhere on Earth, including polar
    regions and lines crossing the antimeridian.
    """
    if line.is_empty:
        return 0.0
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return float(_WGS84.line_length(lons, lats))