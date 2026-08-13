"""
A small self‑contained module that provides a function to compute the length of a
Shapely LineString in meters, using accurate geodesic calculations on the
WGS84 ellipsoid.

Only the standard library and the following third‑party packages are used:
- shapely 2.1
- pyproj 3.7
"""

from __future__ import annotations

from typing import Iterable

from shapely.geometry import LineString
from pyproj import Geod

# Pre‑create a Geod instance for the WGS84 ellipsoid.
# This is cheap and can be reused for all calls.
_geod_wgs84 = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """
    Return the length of a Shapely LineString in metres.

    Parameters
    ----------
    line : shapely.geometry.LineString
        The line whose length is to be computed.  The coordinates must be
        longitude/latitude pairs in EPSG:4326 (WGS84).

    Returns
    -------
    float
        The length of the line in metres.  For a line with fewer than two
        points the function returns 0.0.

    Raises
    ------
    TypeError
        If *line* is not a :class:`shapely.geometry.LineString`.

    Notes
    -----
    The function uses the WGS84 ellipsoid to compute geodesic distances between
    successive vertices.  This approach is accurate anywhere on Earth.
    """
    if not isinstance(line, LineString):
        raise TypeError("line must be a shapely.geometry.LineString")

    coords: Iterable[tuple[float, float]] = list(line.coords)
    if len(coords) < 2:
        return 0.0

    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        # pyproj.Geod.inv returns (azimuth1, azimuth2, distance)
        _, _, dist = _geod_wgs84.inv(lon1, lat1, lon2, lat2)
        total += dist

    return total