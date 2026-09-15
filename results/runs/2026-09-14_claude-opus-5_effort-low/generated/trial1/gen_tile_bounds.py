"""Web Mercator tile bounds for the TMS tiling scheme.

TMS addresses rows from the bottom (y=0 is the southernmost row), unlike the
XYZ/Google scheme where y=0 is the northernmost row.
"""

import math

__all__ = ["tile_bounds"]


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for TMS tile z/x/y.

    Args:
        z: Zoom level (non-negative integer); the grid is 2**z by 2**z tiles.
        x: Tile column, increasing eastward from 0 at -180 degrees.
        y: Tile row, increasing northward from 0 at the southern edge (TMS).

    Returns:
        Tuple of four floats (west, south, east, north).

    Raises:
        ValueError: If z is negative or x/y fall outside the grid for z.
    """
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError("z must be non-negative")
    n = 1 << z
    if not (0 <= x < n) or not (0 <= y < n):
        raise ValueError("x and y must be in [0, 2**z) for zoom %d" % z)

    # Flip the TMS row to the top-origin row used by the standard formulas.
    y_top = n - 1 - y

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y_top / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * (y_top + 1) / n))))

    return (float(west), float(south), float(east), float(north))