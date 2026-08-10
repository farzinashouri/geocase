"""
A small utility module for computing the geodesic length of a shapely LineString
in meters.  The function works for any LineString whose coordinates are
longitude/latitude in EPSG:4326 (WGS84) and is accurate anywhere on Earth.
"""

from __future__ import annotations

from typing import Iterable

from shapely.geometry import LineString
from pyproj import Geod


def length_m(line: LineString) -> float:
    """
    Return the length of *line* in metres, computed using the WGS84 ellipsoid.

    Parameters
    ----------
    line : shapely.geometry.LineString
        A LineString whose coordinates are (lon, lat) in EPSG:4326.

    Returns
    -------
    float
        The total geodesic length of the line in metres.

    Notes
    -----
    The function iterates over each segment of the LineString and sums the
    geodesic distances between consecutive points using :class:`pyproj.Geod`.
    If the LineString has fewer than two points, the length is zero.
    """
    if not isinstance(line, LineString):
        raise TypeError("length_m expects a shapely.geometry.LineString")

    coords: Iterable[tuple[float, float]] = list(line.coords)
    n = len(coords)
    if n < 2:
        return 0.0

    geod = Geod(ellps="WGS84")
    total = 0.0
    for i in range(n - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
        total += dist

    return float(total)