```python
"""Web Mercator tile bounds computation for the TMS tiling scheme."""

import math


def tile_bounds(z, x, y):
    """Return the (west, south, east, north) WGS84 degree bounds of TMS tile (z, x, y)."""
    n = 2 ** z

    def lat(fraction):
        return math.degrees(math.atan(math.sinh(math.pi * (2.0 * fraction - 1.0))))

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    south = lat(y / n)
    north = lat((y + 1) / n)

    return (west, south, east, north)
```