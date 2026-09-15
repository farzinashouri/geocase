"""Geodesic length of EPSG:4326 (WGS84 lon/lat) linestrings, in meters."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from pyproj import Geod
from shapely import get_coordinates
from shapely.geometry import LineString

__all__ = ["length_m"]


@lru_cache(maxsize=1)
def _wgs84_geod() -> Geod:
    """The WGS84 ellipsoid, built on first call so importing this module is inert."""
    return Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the length of ``line`` in meters.

    ``line`` is a shapely ``LineString`` whose coordinates are longitude and
    latitude in EPSG:4326. The result is the sum of the geodesic (shortest-path
    on the WGS84 ellipsoid) distances between consecutive vertices, which is
    accurate anywhere on Earth -- high latitudes, long segments and
    antimeridian crossings included -- without having to pick a projected CRS.

    Empty lines and single-vertex lines return ``0.0``. Any z values are
    ignored, so the result is ground distance, not slope distance.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected a shapely LineString, got {type(line).__name__}")

    coords = get_coordinates(line)  # (N, 2) float64; z is dropped
    if len(coords) < 2:
        return 0.0

    # Pass throwaway copies: pyproj writes the per-segment azimuths back into
    # the buffers it is handed, and column slices are not contiguous anyway.
    lons = np.array(coords[:, 0], dtype=np.float64)
    lats = np.array(coords[:, 1], dtype=np.float64)
    return float(_wgs84_geod().line_length(lons, lats))