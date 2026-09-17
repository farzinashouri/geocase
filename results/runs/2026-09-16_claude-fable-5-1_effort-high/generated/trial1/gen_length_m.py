"""Geodesic length of a WGS84 (EPSG:4326) LineString in meters.

Coordinates are interpreted as (longitude, latitude) pairs. Lengths are
computed on the WGS84 ellipsoid with Karney's geodesic algorithms via
pyproj, so results are accurate anywhere on Earth, including across the
antimeridian and near the poles.
"""

from __future__ import annotations

import math

import numpy as np
from pyproj import Geod
from shapely import get_coordinates
from shapely.geometry import LineString

__all__ = ["length_m"]

_GEOD: Geod | None = None


def _geod() -> Geod:
    """Return a lazily created WGS84 Geod (no work at import time)."""
    global _GEOD
    if _GEOD is None:
        _GEOD = Geod(ellps="WGS84")
    return _GEOD


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line:
        A shapely ``LineString`` with (lon, lat) or (lon, lat, z)
        coordinates in EPSG:4326. Any z values are ignored.

    Returns
    -------
    float
        Length along the WGS84 ellipsoid in meters. Empty or
        single-vertex lines have length 0.0.

    Raises
    ------
    TypeError
        If ``line`` is not a ``LineString``.
    ValueError
        If any coordinate is non-finite or latitude is outside [-90, 90].
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected shapely LineString, got {type(line).__name__}")
    if line.is_empty:
        return 0.0

    coords = get_coordinates(line)  # shape (n, 2); z is dropped
    if coords.shape[0] < 2:
        return 0.0

    lons = np.asarray(coords[:, 0], dtype=float)
    lats = np.asarray(coords[:, 1], dtype=float)

    if not (np.all(np.isfinite(lons)) and np.all(np.isfinite(lats))):
        raise ValueError("LineString contains non-finite coordinates")
    if np.any(np.abs(lats) > 90.0):
        raise ValueError("latitude values must lie within [-90, 90]")

    total = _geod().line_length(lons, lats)
    total = float(total)
    if not math.isfinite(total):
        raise ValueError("geodesic length is not finite")
    return total