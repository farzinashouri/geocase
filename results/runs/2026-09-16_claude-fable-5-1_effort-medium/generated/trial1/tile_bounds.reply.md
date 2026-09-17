```python
"""Web Mercator (EPSG:3857) tile bounds using the TMS tiling scheme.

TMS addresses tiles with row ``y = 0`` at the *southern* edge of the world,
unlike the XYZ/"slippy map" scheme where ``y = 0`` is at the northern edge.
"""

import math

__all__ = ["tile_bounds"]


def _tile_lat(row, n):
    """Latitude (degrees) of the top edge of XYZ row ``row`` at ``n`` tiles per axis."""
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * row / n))))


def tile_bounds(z, x, y):
    """Return ``(west, south, east, north)`` in WGS84 degrees for TMS tile ``(z, x, y)``.

    Parameters
    ----------
    z : int
        Zoom level (>= 0).
    x : int
        Tile column, ``0 <= x < 2**z``, increasing eastward.
    y : int
        Tile row in TMS convention, ``0 <= y < 2**z``, increasing northward.

    Returns
    -------
    tuple of float
        ``(west, south, east, north)`` in degrees.
    """
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError("zoom level must be non-negative")
    n = 1 << z
    if not (0 <= x < n) or not (0 <= y < n):
        raise ValueError(f"tile ({x}, {y}) is out of range for zoom {z}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    # Convert TMS row (origin at south) to XYZ row (origin at north).
    xyz_row = n - 1 - y
    north = _tile_lat(xyz_row, n)
    south = _tile_lat(xyz_row + 1, n)

    return (float(west), float(south), float(east), float(north))
```