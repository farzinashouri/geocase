"""Web Mercator (TMS) tile geographic bounds.

TMS addresses tiles with the row origin at the *bottom* of the map, so row
``y = 0`` is the southernmost row at a given zoom.  This differs from the
XYZ/Google scheme, where row 0 is the northernmost.
"""

from __future__ import annotations

import math

__all__ = ["tile_bounds"]


def _tms_row_latitude(z: int, row: float) -> float:
    """Latitude in degrees of the horizontal line at TMS row edge ``row``.

    ``row`` is measured from the south edge of the map, so ``row = 0`` is the
    southern limit of the projection and ``row = 2 ** z`` is the northern one.
    """
    # Normalized y in [-1, 1], positive northward.
    n = 2.0 * row / (1 << z) - 1.0
    return math.degrees(math.atan(math.sinh(math.pi * n)))


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return ``(west, south, east, north)`` in WGS84 degrees for a TMS tile.

    Parameters
    ----------
    z:
        Zoom level (``z >= 0``).  There are ``2 ** z`` tiles per axis.
    x:
        Tile column, counted eastward from the antimeridian (``-180``).
    y:
        Tile row, counted **northward** from the south edge of the Web
        Mercator extent (TMS convention).

    Raises
    ------
    ValueError
        If ``z`` is negative, or if ``x`` or ``y`` fall outside the valid
        range ``[0, 2 ** z - 1]`` for that zoom.
    TypeError
        If any argument is not an integer.
    """
    for name, value in (("z", z), ("x", x), ("y", y)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an int, got {type(value).__name__}")

    if z < 0:
        raise ValueError(f"z must be non-negative, got {z}")

    n_tiles = 1 << z
    if not 0 <= x < n_tiles:
        raise ValueError(f"x must be in [0, {n_tiles - 1}] at zoom {z}, got {x}")
    if not 0 <= y < n_tiles:
        raise ValueError(f"y must be in [0, {n_tiles - 1}] at zoom {z}, got {y}")

    west = x / n_tiles * 360.0 - 180.0
    east = (x + 1) / n_tiles * 360.0 - 180.0

    # TMS rows increase northward: y is the south edge, y + 1 the north edge.
    south = _tms_row_latitude(z, y)
    north = _tms_row_latitude(z, y + 1)

    return (float(west), float(south), float(east), float(north))