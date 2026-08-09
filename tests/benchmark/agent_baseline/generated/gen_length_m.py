"""Geodesic length of an EPSG:4326 LineString in meters."""

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def length_m(line) -> float:
    """Return the geodesic length in meters of a shapely LineString.

    The LineString's coordinates must be (longitude, latitude) in
    EPSG:4326 / WGS84. Uses Karney's geodesic algorithms on the WGS84
    ellipsoid via pyproj, so results are accurate anywhere on Earth.
    """
    return float(_GEOD.geometry_length(line))
