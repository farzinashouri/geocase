"""
Module for computing the geodesic length of a Shapely LineString in meters.

The function `length_m` takes a LineString with coordinates in EPSG:4326 (longitude, latitude)
and returns its length in meters using the WGS84 ellipsoid.
"""

from pyproj import Geod

# WGS84 ellipsoid
_GEOD = Geod(ellps="WGS84")


def length_m(line) -> float:
    """
    Return the geodesic length of a LineString in meters.

    Parameters
    ----------
    line : shapely.geometry.LineString
        A LineString with coordinates in (longitude, latitude) order (EPSG:4326).

    Returns
    -------
    float
        Length of the line in meters. Returns 0.0 for empty or single-point lines.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons, lats = zip(*coords)
    # pyproj.Geod.line_length expects sequences of longitudes and latitudes
    return float(_GEOD.line_length(lons, lats))