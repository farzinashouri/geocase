"""Geodesic length of WGS84 (EPSG:4326) linework.

Computes true geodesic distance on the WGS84 ellipsoid rather than a
planar/projected approximation, so results are accurate at any latitude and
for segments of any length (including ones crossing the antimeridian, which
a naive projection to a single UTM zone would get badly wrong).
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import Geod

__all__ = ["length_m"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """WGS84 geodesic calculator, built on first use so import is side-effect free."""
    return Geod(ellps="WGS84")


def length_m(line) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line:
        A shapely ``LineString`` (or ``LinearRing``) whose coordinates are
        ``(longitude, latitude)`` in degrees, EPSG:4326. Any ``z`` values are
        ignored: the result is horizontal ground distance.

    Returns
    -------
    float
        Length in meters; ``0.0`` for an empty geometry or a single point.
    """
    if line is None:
        raise TypeError("line must be a shapely LineString, not None")
    if line.is_empty:
        return 0.0

    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    # line_length sums the geodesic distance between consecutive vertices.
    return float(_geod().line_length(lons, lats))