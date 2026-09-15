"""Geographic bounds of Web Mercator tiles addressed in the TMS scheme."""

from __future__ import annotations

import math
import operator

__all__ = ["tile_bounds"]


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return ``(west, south, east, north)`` in WGS84 degrees for one tile.

    The grid is the Web Mercator (EPSG:3857) quadtree: zoom ``z`` cuts the
    world into ``2 ** z`` columns and ``2 ** z`` rows of equal size in
    projected space. Addressing follows the TMS convention, so row ``y = 0``
    is the *southernmost* row and ``y`` counts northward -- the opposite of
    the XYZ/slippy-map convention, whose row 0 is at the top. Translate
    between the two with ``y_xyz = 2 ** z - 1 - y_tms``.

    Raises:
        ValueError: if ``z`` is negative, or ``x``/``y`` fall outside the grid.
        TypeError: if any argument is not an integer.
    """
    z, x, y = operator.index(z), operator.index(x), operator.index(y)
    if z < 0:
        raise ValueError(f"zoom must be non-negative, got {z}")

    n = 1 << z  # tiles per axis
    if not (0 <= x < n and 0 <= y < n):
        raise ValueError(f"tile ({x}, {y}) is outside the {n}x{n} grid at zoom {z}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    south = _mercator_lat(2.0 * y / n - 1.0)
    north = _mercator_lat(2.0 * (y + 1) / n - 1.0)
    return (west, south, east, north)


def _mercator_lat(fraction: float) -> float:
    """Latitude in degrees ``fraction`` of the way up the Mercator y range (-1 south, 1 north)."""
    return math.degrees(math.atan(math.sinh(math.pi * fraction)))