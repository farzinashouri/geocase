"""Geodesic length of an EPSG:4326 (WGS84 lon/lat) LineString in meters.

Uses pyproj's Geod on the WGS84 ellipsoid (Karney's geodesic algorithms),
which is accurate to sub-millimetre precision anywhere on Earth, including
antimeridian crossings and polar regions.
"""

from __future__ import annotations

from pyproj import Geod
from shapely.geometry import LineString

__all__ = ["length_m"]

_WGS84 = Geod(ellps="WGS84")


def length_m(line: LineString) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line:
        A shapely ``LineString`` whose coordinates are (longitude, latitude)
        in EPSG:4326. A trailing Z coordinate, if present, is ignored.

    Returns
    -------
    float
        Length along the WGS84 ellipsoid in meters. Empty or single-point
        lines return ``0.0``.
    """
    if not isinstance(line, LineString):
        raise TypeError(f"expected shapely LineString, got {type(line).__name__}")

    if line.is_empty:
        return 0.0

    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons = [float(c[0]) for c in coords]
    lats = [float(c[1]) for c in coords]

    return float(_WGS84.line_length(lons, lats))