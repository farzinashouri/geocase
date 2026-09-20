"""Geographic bounds of Web Mercator tiles addressed in the TMS scheme.

TMS numbers rows from the south (bottom) edge upward, unlike the XYZ/"slippy
map" scheme which numbers rows from the north. Tiles are assumed to be in the
standard EPSG:3857 grid with a single tile at zoom 0 covering the full world
between roughly -85.0511 and 85.0511 degrees latitude.
"""

import math

__all__ = ["tile_bounds"]


def _mercator_fraction_to_lat(fraction):
    """Convert a vertical fraction of the world (0 = south edge, 1 = north edge)
    into a WGS84 latitude in degrees."""
    return math.degrees(math.atan(math.sinh(math.pi * (2.0 * fraction - 1.0))))


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for TMS tile z/x/y.

    Args:
        z: Zoom level, a non-negative integer.
        x: Tile column, 0 at the west edge, in range [0, 2**z).
        y: Tile row, 0 at the south edge (TMS), in range [0, 2**z).

    Returns:
        A tuple of four floats: (west, south, east, north).
    """
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError("zoom level must be non-negative, got %r" % (z,))
    n = 2 ** z
    if not 0 <= x < n:
        raise ValueError("tile column %r out of range for zoom %r" % (x, z))
    if not 0 <= y < n:
        raise ValueError("tile row %r out of range for zoom %r" % (y, z))

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    south = _mercator_fraction_to_lat(y / n)
    north = _mercator_fraction_to_lat((y + 1) / n)

    return (float(west), float(south), float(east), float(north))