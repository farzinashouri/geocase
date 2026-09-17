```python
"""Geographic extent of a Web Mercator tile addressed in the TMS scheme.

TMS numbers rows from the south (y = 0 is the bottom row), unlike the
XYZ/"slippy map" scheme where y = 0 is the top row.
"""

import math

__all__ = ["tile_bounds"]

_MAX_LAT = math.degrees(math.atan(math.sinh(math.pi)))  # ~85.0511287798


def _tile_lon(x, n):
    """Longitude (degrees) of the west edge of column ``x`` at ``n`` tiles per axis."""
    return x / n * 360.0 - 180.0


def _tile_lat(y_xyz, n):
    """Latitude (degrees) of the top edge of XYZ row ``y_xyz`` at ``n`` tiles per axis."""
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y_xyz / n))))


def tile_bounds(z, x, y):
    """Return ``(west, south, east, north)`` in WGS84 degrees for TMS tile ``z/x/y``.

    Parameters
    ----------
    z : int
        Zoom level (>= 0).
    x : int
        Tile column, 0 <= x < 2**z, increasing eastward.
    y : int
        Tile row in the TMS scheme, 0 <= y < 2**z, increasing northward
        (row 0 touches the southern limit of the Web Mercator extent).

    Returns
    -------
    tuple of float
        ``(west, south, east, north)`` longitude/latitude bounds in degrees.
    """
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError(f"zoom must be >= 0, got {z}")
    n = 1 << z
    if not 0 <= x < n:
        raise ValueError(f"x must be in [0, {n}), got {x}")
    if not 0 <= y < n:
        raise ValueError(f"y must be in [0, {n}), got {y}")

    west = _tile_lon(x, n)
    east = _tile_lon(x + 1, n) if x + 1 < n else 180.0

    # Convert the TMS row to the equivalent XYZ (top-origin) row.
    y_xyz = n - 1 - y
    north = _tile_lat(y_xyz, n) if y_xyz > 0 else _MAX_LAT
    south = _tile_lat(y_xyz + 1, n) if y_xyz + 1 < n else -_MAX_LAT

    return (float(west), float(south), float(east), float(north))
```