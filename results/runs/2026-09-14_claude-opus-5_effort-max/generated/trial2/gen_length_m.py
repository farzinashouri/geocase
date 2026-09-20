"""Geodesic length of EPSG:4326 (WGS84) linestrings.

``length_m`` measures a shapely ``LineString`` whose coordinates are
(longitude, latitude) in degrees, treating each segment between consecutive
vertices as a geodesic on the WGS84 ellipsoid and returning the total length
in meters.  It delegates to pyproj's implementation of Karney's geodesic
algorithms, which is accurate to well under a millimeter per segment anywhere
on Earth -- high latitudes, very long segments, and antimeridian crossings
included -- so no projection needs to be chosen for the input's location.
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import Geod

__all__ = ["length_m"]


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """Return the shared WGS84 ``Geod``, built on first call so import is inert."""
    return Geod(ellps="WGS84")


def length_m(line) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line:
        A shapely ``LineString`` (a ``LinearRing`` works too) with EPSG:4326
        longitude/latitude coordinates in degrees.  Z values, if present, are
        ignored: the result is the distance travelled over the ellipsoid
        surface, not the slope distance.

    Returns
    -------
    float
        Length in meters.  Empty geometries measure ``0.0``.
    """
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0

    # Fresh lists rather than the geometry's own buffers, so the caller's
    # coordinates are never handed to (or touched by) the pyproj backend.
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return float(_geod().line_length(lons, lats))