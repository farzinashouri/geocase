"""Compute WGS84 geographic bounds of a Web Mercator tile (TMS scheme)."""

import math


def _mercator_lat(fraction):
    """Convert a fractional row position (0=north edge, 1=south edge) to latitude in degrees."""
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * fraction))))


def tile_bounds(z, x, y):
    """Return (west, south, east, north) WGS84 degree bounds of TMS tile (z, x, y)."""
    n = 2 ** z
    y_xyz = n - 1 - y  # TMS row -> standard XYZ row (origin at north)

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = _mercator_lat(y_xyz / n)
    south = _mercator_lat((y_xyz + 1) / n)

    return (float(west), float(south), float(east), float(north))