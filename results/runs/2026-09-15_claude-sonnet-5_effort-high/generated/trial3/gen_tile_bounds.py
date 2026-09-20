"""Tile bounds computation for TMS-scheme Web Mercator tiles."""

import math


def tile_bounds(z, x, y):
    """Return (west, south, east, north) WGS84 degree bounds of TMS tile (z, x, y)."""
    n = 2 ** z

    def _lat(row):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * row / n))))

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    xyz_row = n - 1 - y
    north = _lat(xyz_row)
    south = _lat(xyz_row + 1)

    return (west, south, east, north)