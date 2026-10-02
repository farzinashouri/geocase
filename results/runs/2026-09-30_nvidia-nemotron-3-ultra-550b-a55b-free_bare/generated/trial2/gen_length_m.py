"""
Module for computing the geodesic length of a LineString in meters.

Uses pyproj's Geod class with the WGS84 ellipsoid for accurate global results.
"""

from pyproj import Geod
from shapely.geometry import LineString

# Geod instance for WGS84 (EPSG:4326)
_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """
    Return the length of a LineString in meters using geodesic calculation.

    Parameters
    ----------
    line : shapely.geometry.LineString
        A LineString with coordinates in EPSG:4326 (longitude, latitude).

    Returns
    -------
    float
        Length in meters. Returns 0.0 for empty or single-point lines.
    """
    if line.is_empty:
        return 0.0

    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    # pyproj.Geod.line_length expects a sequence of (lon, lat) points.
    return _GEOD.line_length(coords)