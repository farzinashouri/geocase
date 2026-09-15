"""Compute geodesic length of a WGS84 longitude/latitude LineString in meters."""

from pyproj import Geod
from shapely.geometry import LineString

_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of a lon/lat LineString in meters."""
    lons = [coord[0] for coord in line.coords]
    lats = [coord[1] for coord in line.coords]
    length, = (_GEOD.line_length(lons, lats),)
    return float(length)