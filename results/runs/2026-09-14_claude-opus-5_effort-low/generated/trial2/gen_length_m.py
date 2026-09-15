"""Geodesic length of a WGS84 (EPSG:4326) LineString, in meters."""

from pyproj import Geod
from shapely.geometry import LineString

# WGS84 ellipsoid; module-level construction is pure (no I/O, no global state).
_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    ``line`` must be a shapely ``LineString`` with (longitude, latitude)
    coordinates in EPSG:4326. Any Z values are ignored: the result is the
    length along the WGS84 ellipsoid surface, accurate anywhere on Earth
    (sub-millimeter for typical segment lengths).
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    # line_length sums the geodesic distance over consecutive vertex pairs.
    return float(_GEOD.line_length(lons, lats))