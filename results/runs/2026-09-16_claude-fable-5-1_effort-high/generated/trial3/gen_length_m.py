"""Geodesic length of an EPSG:4326 LineString in meters.

Uses pyproj's WGS84 geodesic (Karney's algorithm), which is accurate to
sub-millimeter precision anywhere on Earth, including near the poles and
across the antimeridian.
"""

from __future__ import annotations

import math

from pyproj import Geod
from shapely.geometry import LineString

_WGS84_GEOD = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line:
        A shapely ``LineString`` whose coordinates are longitude, latitude
        (degrees) in EPSG:4326. Any Z or M ordinates are ignored.

    Returns
    -------
    float
        Length along the WGS84 ellipsoid in meters. Empty lines and lines
        with fewer than two vertices return ``0.0``.
    """
    if line is None or line.is_empty:
        return 0.0

    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    total = 0.0
    for i in range(len(coords) - 1):
        lon1, lat1 = lons[i], lats[i]
        lon2, lat2 = lons[i + 1], lats[i + 1]
        if lon1 == lon2 and lat1 == lat2:
            continue
        _, _, dist = _WGS84_GEOD.inv(lon1, lat1, lon2, lat2)
        if math.isnan(dist):
            raise ValueError(
                f"Geodesic computation failed for segment "
                f"({lon1}, {lat1}) -> ({lon2}, {lat2})"
            )
        total += dist

    return float(total)