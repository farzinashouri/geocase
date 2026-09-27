```python
"""Compute the WGS84 geographic bounds of a Web Mercator tile addressed
with the TMS tiling scheme."""

import math


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for the TMS tile
    at zoom ``z``, column ``x``, row ``y``.

    In the TMS scheme the row origin is at the bottom (south) of the map,
    so ``y`` is flipped relative to the Google/XYZ ("slippy map") scheme
    before applying the standard Web Mercator inverse.
    """
    n = 2 ** z

    # Flip the TMS row to the XYZ row convention (origin at top/north).
    y_xyz = n - 1 - y

    def lon(xt):
        return xt / n * 360.0 - 180.0

    def lat(yt):
        # Inverse Web Mercator: yt runs from 0 (north) to n (south).
        merc = math.pi * (1.0 - 2.0 * yt / n)
        return math.degrees(math.atan(math.sinh(merc)))

    west = lon(x)
    east = lon(x + 1)
    north = lat(y_xyz)
    south = lat(y_xyz + 1)

    return (west, south, east, north)
```