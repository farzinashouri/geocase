```python
"""Web Mercator (TMS scheme) tile bounds in WGS84 degrees."""

import math

__all__ = ["tile_bounds"]


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for TMS tile z/x/y.

    TMS rows are numbered from the south (y=0 is the bottom row), unlike the
    XYZ/Google scheme where row 0 is the northernmost.
    """
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError("zoom must be non-negative")
    n = 1 << z
    if not (0 <= x < n and 0 <= y < n):
        raise ValueError("tile column/row out of range for zoom %d" % z)

    # Flip TMS row (origin south) to XYZ row (origin north).
    y_xyz = n - 1 - y

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y_xyz / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * (y_xyz + 1) / n))))

    return (float(west), float(south), float(east), float(north))
```