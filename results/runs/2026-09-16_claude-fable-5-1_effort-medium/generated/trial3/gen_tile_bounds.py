"""Geographic bounds of Web Mercator tiles addressed with the TMS scheme.

TMS differs from the XYZ/"slippy map" scheme only in the row direction:
TMS row 0 is the southernmost row, XYZ row 0 is the northernmost.
"""

import math

# Latitude limit of the square Web Mercator (EPSG:3857) world extent.
MAX_LATITUDE = math.degrees(2.0 * math.atan(math.exp(math.pi)) - math.pi / 2.0)


def _column_to_lon(z: int, x: float) -> float:
    n = 2 ** z
    return x / n * 360.0 - 180.0


def _xyz_row_to_lat(z: int, y: float) -> float:
    n = 2 ** z
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for TMS tile (z, x, y).

    Raises ValueError if the zoom is negative or the tile index is outside
    the valid range for that zoom.
    """
    z, x, y = int(z), int(x), int(y)
    if z < 0:
        raise ValueError(f"zoom must be non-negative, got {z}")
    n = 2 ** z
    if not (0 <= x < n) or not (0 <= y < n):
        raise ValueError(f"tile ({x}, {y}) out of range for zoom {z}")

    # Convert TMS row to XYZ row so that the north edge comes from y_xyz
    # and the south edge from y_xyz + 1.
    y_xyz = n - 1 - y

    west = _column_to_lon(z, x)
    east = _column_to_lon(z, x + 1)
    north = _xyz_row_to_lat(z, y_xyz)
    south = _xyz_row_to_lat(z, y_xyz + 1)

    # Clamp to the exact Mercator limits to avoid floating-point overshoot.
    north = min(north, MAX_LATITUDE)
    south = max(south, -MAX_LATITUDE)

    return (float(west), float(south), float(east), float(north))