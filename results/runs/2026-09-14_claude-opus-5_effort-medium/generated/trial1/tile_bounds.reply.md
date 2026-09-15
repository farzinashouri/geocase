```python
"""Geographic extent of Web Mercator tiles addressed in the TMS scheme.

TMS (Tile Map Service) numbers rows from the *bottom* of the map upward, so row
0 is the southernmost row at any zoom level.  This differs from the "slippy
map" / XYZ convention used by most web map clients, where row 0 is the
northernmost.  The two differ only by a flip of the row index:

    y_xyz = 2**z - 1 - y_tms
"""

import math

__all__ = ["tile_bounds"]


def tile_bounds(z, x, y):
    """Return the WGS84 extent of the TMS tile ``(z, x, y)``.

    Parameters
    ----------
    z : int
        Zoom level; the map is divided into ``2**z`` columns and rows.
    x : int
        Tile column, counted eastward from 0 at longitude -180.
    y : int
        Tile row, counted *northward* from 0 at the southern edge of the
        Web Mercator extent (TMS convention).

    Returns
    -------
    tuple of float
        ``(west, south, east, north)`` in decimal degrees.  Longitudes lie in
        [-180, 180]; latitudes lie within the Web Mercator limits of
        approximately +/- 85.0511287798.
    """
    z = int(z)
    x = int(x)
    y = int(y)

    if z < 0:
        raise ValueError("zoom must be non-negative, got {!r}".format(z))

    n = 2 ** z
    if not (0 <= x < n and 0 <= y < n):
        raise ValueError(
            "tile ({}, {}, {}) is outside the valid range 0..{} at this zoom"
            .format(z, x, y, n - 1)
        )

    # Flip the TMS row to the top-down row used by the standard formulas.
    y_top = n - 1 - y

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    north = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y_top / n))))
    south = math.degrees(
        math.atan(math.sinh(math.pi * (1.0 - 2.0 * (y_top + 1) / n)))
    )

    return (float(west), float(south), float(east), float(north))
```