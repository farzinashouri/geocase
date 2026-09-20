```python
"""Web Mercator tile bounds using the TMS tiling scheme.

In TMS, tile row 0 is at the bottom (south), unlike the XYZ/Slippy scheme
where row 0 is at the top (north).
"""

import math

_MAX_LAT = 85.05112877980659


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for TMS tile z/x/y."""
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError("zoom must be non-negative")
    n = 2 ** z
    if not (0 <= x < n) or not (0 <= y < n):
        raise ValueError("tile x/y out of range for zoom level")

    def lon(col):
        return col / n * 360.0 - 180.0

    def lat(row_from_top):
        # Rows measured from the top, as in the XYZ scheme.
        t = math.pi * (1.0 - 2.0 * row_from_top / n)
        return math.degrees(math.atan(math.sinh(t)))

    # Convert TMS row (origin bottom) to XYZ row (origin top).
    y_xyz = n - 1 - y

    west = lon(x)
    east = lon(x + 1)
    north = lat(y_xyz)
    south = lat(y_xyz + 1)

    # Clamp to the Web Mercator latitude limit to absorb floating-point drift.
    north = max(-_MAX_LAT, min(_MAX_LAT, north))
    south = max(-_MAX_LAT, min(_MAX_LAT, south))

    return (float(west), float(south), float(east), float(north))
```