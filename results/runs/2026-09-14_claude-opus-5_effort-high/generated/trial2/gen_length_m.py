"""Geodesic length of EPSG:4326 (WGS84) linestrings.

Coordinates are interpreted as (longitude, latitude) in degrees, matching the
EPSG:4326 axis order used by shapely/GeoJSON. Length is computed segment by
segment with Karney's geodesic algorithm on the WGS84 ellipsoid, so it is
accurate (sub-millimetre per segment) anywhere on Earth, including at the poles
and across the antimeridian, with no projection or UTM-zone selection needed.

Importing this module performs no I/O and has no side effects.
"""

from __future__ import annotations

import numpy as np
from pyproj import Geod
from shapely.geometry import LineString

# Pure in-memory ellipsoid definition; constructing it touches no external state.
_GEOD = Geod(ellps="WGS84")

__all__ = ["length_m"]


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line:
        A shapely ``LineString`` whose coordinates are longitude/latitude
        degrees in EPSG:4326. A ``Z`` dimension, if present, is ignored: the
        result is the length measured along the ellipsoid surface.

    Returns
    -------
    float
        Length in meters. Empty or single-point linestrings yield ``0.0``.
    """
    coords = np.asarray(line.coords, dtype=float)
    if coords.ndim != 2 or coords.shape[0] < 2:
        return 0.0

    lons = coords[:, 0]
    lats = coords[:, 1]
    return float(_GEOD.line_length(lons, lats))