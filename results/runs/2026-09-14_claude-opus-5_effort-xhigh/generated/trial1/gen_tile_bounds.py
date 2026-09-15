"""Geographic extent of Web Mercator (EPSG:3857) map tiles addressed with TMS.

The TMS tiling scheme splits the Web Mercator square into ``2**z`` columns and
``2**z`` rows at zoom ``z``.  Column ``x`` increases eastward from the antimeridian
and row ``y`` increases *northward* from the southern edge of the projection's
valid area (row 0 is the southernmost row), which is the one difference from the
otherwise identical XYZ/"slippy map" scheme.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
from operator import index as _as_int

__all__ = ["tile_bounds"]

# Latitude cutoff of the Web Mercator square: atan(sinh(pi)) in degrees.
_MAX_LATITUDE = math.degrees(math.atan(math.sinh(math.pi)))


def _latitude(fraction_from_south: float) -> float:
    """Latitude in degrees of the horizontal line lying ``fraction_from_south``
    of the way up the Web Mercator square (0.0 = south edge, 1.0 = north edge).

    Inverts the spherical Mercator projection: the normalized northing
    ``t = 2 * fraction - 1`` maps to ``lat = atan(sinh(pi * t))``.
    """
    return math.degrees(math.atan(math.sinh(math.pi * (2.0 * fraction_from_south - 1.0))))


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return the WGS84 extent of the TMS tile ``(z, x, y)``.

    Parameters
    ----------
    z : int
        Zoom level, ``z >= 0``.
    x : int
        Tile column, ``0 <= x < 2**z``, increasing eastward.
    y : int
        Tile row, ``0 <= y < 2**z``, increasing northward (TMS convention).

    Returns
    -------
    tuple of four floats
        ``(west, south, east, north)`` in degrees of longitude/latitude.
        Longitudes span ``[-180, 180]``; latitudes are bounded by the Web
        Mercator cutoff of about +/- 85.0511 degrees.

    Raises
    ------
    TypeError
        If ``z``, ``x`` or ``y`` is not an integer.
    ValueError
        If ``z`` is negative, or ``x``/``y`` fall outside the tile grid at ``z``.
    """
    z = _as_int(z)
    x = _as_int(x)
    y = _as_int(y)

    if z < 0:
        raise ValueError(f"zoom must be non-negative, got {z}")

    n = 1 << z
    if not 0 <= x < n:
        raise ValueError(f"x must be in [0, {n - 1}] at zoom {z}, got {x}")
    if not 0 <= y < n:
        raise ValueError(f"y must be in [0, {n - 1}] at zoom {z}, got {y}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    # Snap the outermost rows to the exact projection limits so that repeated
    # trigonometry does not leave the poles a few ULPs short.
    south = -_MAX_LATITUDE if y == 0 else _latitude(y / n)
    north = _MAX_LATITUDE if y == n - 1 else _latitude((y + 1) / n)

    return (float(west), float(south), float(east), float(north))