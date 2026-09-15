"""Geodesic length of a WGS84 LineString, in meters."""

from pyproj import Geod
from shapely.geometry import LineString

_WGS84_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length in meters of a lon/lat (EPSG:4326) LineString.

    Uses inverse geodesic solutions on the WGS84 ellipsoid, so the result is
    accurate anywhere on Earth and does not depend on a local projection.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    # geometry_length would re-read the geometry; line_length sums segment
    # geodesics directly from the vertex sequence (ignoring any z values).
    return float(_WGS84_GEOD.line_length(lons, lats))