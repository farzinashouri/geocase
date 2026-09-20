"""Geodesic length of WGS84 (EPSG:4326) linestrings, in meters."""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import LineString

# Constructing a Geod is pure in-process setup: no I/O, no global state mutation.
_WGS84 = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    ``line`` must be a shapely ``LineString`` whose coordinates are
    (longitude, latitude) in degrees on EPSG:4326. Any Z values are ignored;
    the result is the length along the WGS84 ellipsoid surface, which is
    accurate anywhere on Earth (including near the poles and across the
    antimeridian, as long as consecutive vertices are given in the sense the
    line is meant to be traversed).
    """
    if line.is_empty:
        return 0.0

    coords = line.coords
    if len(coords) < 2:
        return 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    # geometry_length/line_length sum the inverse geodesic distances between
    # consecutive vertices, so the result follows great-ellipse arcs rather
    # than treating degrees as planar units.
    return float(_WGS84.line_length(lons, lats))