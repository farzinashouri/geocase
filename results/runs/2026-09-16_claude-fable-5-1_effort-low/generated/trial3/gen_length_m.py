"""Geodesic length of an EPSG:4326 LineString in meters."""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import LineString

_WGS84 = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    ``line`` must be a shapely ``LineString`` with coordinates ordered as
    (longitude, latitude) in EPSG:4326. Length is computed on the WGS84
    ellipsoid, so results are accurate at any latitude and for lines that
    cross the antimeridian or pass near the poles.
    """
    if line.is_empty:
        return 0.0
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    _, _, dists = _WGS84.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
    return float(sum(dists))