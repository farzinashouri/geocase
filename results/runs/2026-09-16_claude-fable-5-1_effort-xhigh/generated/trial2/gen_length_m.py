"""Geodesic length of an EPSG:4326 (WGS84 lon/lat) LineString, in meters."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import shapely
from pyproj import Geod
from shapely.geometry import LineString


@lru_cache(maxsize=1)
def _wgs84() -> Geod:
    # Built lazily so importing this module does no work.
    return Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    ``line`` must be a shapely ``LineString`` (or ``LinearRing``) whose
    coordinates are longitude/latitude degrees on WGS84 (EPSG:4326).
    Each segment is measured along the ellipsoidal geodesic using
    Karney's algorithm (via PROJ), so results are accurate everywhere
    on Earth, including across the antimeridian, near the poles, and
    for near-antipodal endpoints.  Any Z/M values are ignored.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected a shapely LineString, got {type(line).__name__}")
    if line.is_empty:
        return 0.0

    coords = shapely.get_coordinates(line)  # shape (n, 2): lon, lat
    if len(coords) < 2:
        return 0.0

    lons = np.ascontiguousarray(coords[:, 0], dtype=np.float64)
    lats = np.ascontiguousarray(coords[:, 1], dtype=np.float64)
    if not (np.all(np.isfinite(lons)) and np.all(np.abs(lats) <= 90.0)):
        raise ValueError("coordinates must be finite lon/lat degrees with |lat| <= 90")

    return float(_wgs84().line_length(lons, lats))