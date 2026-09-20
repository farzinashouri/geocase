"""Geodesic length of an EPSG:4326 (WGS84) LineString, in meters."""

from __future__ import annotations

import numpy as np
import shapely
from pyproj import Geod
from shapely.geometry import LineString

# Geodesic solver on the WGS84 ellipsoid. Constructing it is a pure
# computation with no I/O, so importing this module has no side effects.
_WGS84 = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the length of ``line`` in meters.

    ``line`` is a shapely ``LineString`` whose coordinates are
    (longitude, latitude) in EPSG:4326. Each segment is measured as a
    geodesic on the WGS84 ellipsoid using Karney's algorithm (via
    pyproj/PROJ), which is accurate to well under a millimeter for any
    pair of points on Earth, including antipodal points, segments that
    cross the antimeridian, and segments near the poles.

    Any Z coordinate is ignored. An empty or single-point line has
    length 0.0. Longitudes outside [-180, 180] are handled.
    """
    if not isinstance(line, LineString):
        raise TypeError(
            f"length_m expects a shapely LineString, got {type(line).__name__}"
        )
    if line.is_empty:
        return 0.0

    coords = shapely.get_coordinates(line)  # shape (n, 2): lon, lat; z dropped
    if coords.shape[0] < 2:
        return 0.0

    lon = np.asarray(coords[:, 0], dtype=float)
    lat = np.asarray(coords[:, 1], dtype=float)
    _, _, seg_lengths = _WGS84.inv(lon[:-1], lat[:-1], lon[1:], lat[1:])
    return float(np.sum(seg_lengths))