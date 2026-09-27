"""Geodesic length of a WGS84 (EPSG:4326) LineString, in meters."""

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def length_m(line):
    """Return the geodesic length in meters of a shapely LineString.

    The line's coordinates are interpreted as (longitude, latitude) in
    EPSG:4326 (WGS84). Accurate anywhere on Earth.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return float(_GEOD.line_length(lons, lats))