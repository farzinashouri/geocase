"""Geodesic length of an EPSG:4326 LineString in meters."""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import LineString

_WGS84 = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length in meters of a lon/lat (EPSG:4326) LineString.

    Each segment is measured along the WGS84 ellipsoid using Karney's
    geodesic algorithms (via pyproj), so results are accurate anywhere on
    Earth, including across the antimeridian and near the poles.
    """
    if line.is_empty:
        return 0.0
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return float(_WGS84.line_length(lons, lats))