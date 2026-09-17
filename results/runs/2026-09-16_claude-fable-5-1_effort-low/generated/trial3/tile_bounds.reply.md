```python
"""Web Mercator tile bounds for TMS-addressed tiles."""

import math

_MAX_LAT = math.degrees(2 * math.atan(math.exp(math.pi)) - math.pi / 2)


def _lat_from_mercator_y(y_frac):
    """Map a fraction in [0, 1] (0 = south edge of world) to latitude degrees."""
    merc_y = (2 * y_frac - 1) * math.pi
    return math.degrees(2 * math.atan(math.exp(merc_y)) - math.pi / 2)


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for TMS tile z/x/y.

    In the TMS scheme row 0 is the southernmost row (y increases northward),
    unlike the XYZ/slippy-map scheme where row 0 is northernmost.
    """
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError("zoom must be non-negative")
    n = 2 ** z
    if not (0 <= x < n) or not (0 <= y < n):
        raise ValueError("tile x/y out of range for zoom %d" % z)

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    south = _lat_from_mercator_y(y / n)
    north = _lat_from_mercator_y((y + 1) / n)

    # Clamp edges to exact bounds to avoid floating-point drift at the world edge.
    if y == 0:
        south = -_MAX_LAT
    if y == n - 1:
        north = _MAX_LAT
    if x == n - 1:
        east = 180.0

    return (float(west), float(south), float(east), float(north))
```