"""Geodesic length of a WGS84 (EPSG:4326) LineString, in meters."""

from pyproj import Geod
from shapely.geometry import LineString

_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length in meters of a lon/lat LineString.

    Coordinates are interpreted as (longitude, latitude) in EPSG:4326
    (WGS84). Length is computed as the sum of geodesic distances between
    consecutive vertices on the WGS84 ellipsoid, so it is accurate
    anywhere on Earth. Any Z components are ignored.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    total = 0.0
    for i in range(len(coords) - 1):
        _, _, dist = _GEOD.inv(lons[i], lats[i], lons[i + 1], lats[i + 1])
        total += dist
    return float(total)