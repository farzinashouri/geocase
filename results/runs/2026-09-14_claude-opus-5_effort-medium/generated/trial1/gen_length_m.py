"""Geodesic length of WGS84 (EPSG:4326) LineStrings.

Planar length on lon/lat degrees is meaningless as meters, and a single
projected CRS (UTM, Web Mercator, ...) is only accurate in a limited band.
Instead we integrate the true geodesic distance between consecutive vertices
on the WGS84 ellipsoid, which is accurate anywhere on Earth and handles
antimeridian crossings (the inverse solution always takes the short way
around).
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import Geod
from shapely.geometry.base import BaseGeometry

__all__ = ["length_m"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """WGS84 ellipsoid, built lazily so importing this module does nothing."""
    return Geod(ellps="WGS84")


def length_m(line) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line
        A shapely ``LineString`` (or ``LinearRing``) whose coordinates are
        ``(longitude, latitude)`` in degrees, EPSG:4326. Any Z values are
        ignored: the result is the length along the ellipsoid surface.

    Returns
    -------
    float
        Length in meters. Empty geometries and single-vertex inputs give 0.0.
    """
    if not isinstance(line, BaseGeometry):
        raise TypeError(f"expected a shapely geometry, got {type(line).__name__}")
    if line.geom_type not in ("LineString", "LinearRing"):
        raise TypeError(f"expected a LineString, got {line.geom_type}")
    if line.is_empty:
        return 0.0

    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    # line_length sums the geodesic distances of consecutive vertex pairs.
    return float(_geod().line_length(lons, lats))