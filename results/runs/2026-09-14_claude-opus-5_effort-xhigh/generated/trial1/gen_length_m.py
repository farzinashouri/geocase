"""Geodesic length of WGS84 (EPSG:4326) line geometries.

Planar length (``shapely``'s ``LineString.length``) is meaningless on lon/lat
input, and projecting to a single metric CRS is only accurate near that CRS's
region of validity. Measuring each segment as a geodesic on the WGS84
ellipsoid instead is accurate to sub-millimeter anywhere on Earth.
"""

from __future__ import annotations

import numpy as np
import shapely
from pyproj import Geod

# Constructing a Geod is pure computation (no I/O, no global state), so module
# import stays side-effect free.
_GEOD = Geod(ellps="WGS84")

_LINE_TYPES = ("LineString", "LinearRing")


def length_m(line) -> float:
    """Return the geodesic length, in meters, of a lon/lat line.

    Parameters
    ----------
    line:
        A shapely ``LineString`` (or ``LinearRing``) whose coordinates are
        ``(longitude, latitude)`` in degrees, EPSG:4326.

    Returns
    -------
    float
        Length in meters along WGS84 geodesics. Correct at any latitude and
        across the antimeridian, where consecutive vertices are joined by the
        shorter geodesic (e.g. 179°E to 179°W is ~222 km, not ~40000 km).
        Empty geometries and single-vertex lines return ``0.0``; any z values
        are ignored, so this is ground distance, not slope distance.

    Raises
    ------
    ValueError
        If ``line`` is not a line geometry, or has non-finite coordinates.
    """
    geom_type = getattr(line, "geom_type", None)
    if geom_type not in _LINE_TYPES:
        raise ValueError(
            f"expected a LineString or LinearRing, got {geom_type or type(line).__name__!r}"
        )

    # (n, 2) array of lon/lat; z is dropped rather than folded into the length.
    coords = shapely.get_coordinates(line)
    if len(coords) < 2:
        return 0.0
    if not np.isfinite(coords).all():
        raise ValueError("line has non-finite coordinates")

    return float(_GEOD.line_length(coords[:, 0], coords[:, 1]))