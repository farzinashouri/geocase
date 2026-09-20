"""Geodesic length of an EPSG:4326 LineString in meters."""

from __future__ import annotations

import math

import numpy as np
from pyproj import Geod
from shapely.geometry import LineString

_WGS84 = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length in meters of a WGS84 (lon/lat) LineString.

    Uses Karney's geodesic algorithm via pyproj, so the result is accurate
    (sub-millimeter) anywhere on Earth, including across the antimeridian
    and near the poles.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected a shapely LineString, got {type(line).__name__}")
    if line.is_empty:
        return 0.0

    coords = np.asarray(line.coords, dtype=float)
    if coords.shape[0] < 2:
        return 0.0

    lons = coords[:, 0]
    lats = coords[:, 1]
    if not (np.all(np.isfinite(lons)) and np.all(np.isfinite(lats))):
        raise ValueError("LineString contains non-finite coordinates")
    if np.any(np.abs(lats) > 90.0):
        raise ValueError("latitude out of range [-90, 90]")

    _, _, dists = _WGS84.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
    total = float(np.sum(dists))
    if not math.isfinite(total):
        raise ValueError("geodesic length computation failed")
    return total