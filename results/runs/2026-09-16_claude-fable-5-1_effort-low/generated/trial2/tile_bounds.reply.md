```python
"""Web Mercator tile bounds using the TMS tiling scheme.

TMS differs from the XYZ/"slippy map" scheme only in the row direction:
row 0 is the southernmost row (y increases northward).
"""

import math

_WEBMERCATOR_MAX_LAT = math.degrees(math.atan(math.sinh(math.pi)))  # ~85.0511


def _tile_lat(z, y_xyz):
    """Latitude of the top edge of XYZ row ``y_xyz`` at zoom ``z``."""
    n = 2 ** z
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y_xyz / n))))


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for TMS tile (z, x, y)."""
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError("zoom must be non-negative")
    n = 2 ** z
    if not (0 <= x < n and 0 <= y < n):
        raise ValueError(f"tile ({x}, {y}) out of range for zoom {z}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    # Convert TMS row (0 at south) to XYZ row (0 at north).
    y_xyz = n - 1 - y
    north = _tile_lat(z, y_xyz)
    south = _tile_lat(z, y_xyz + 1)

    # Clamp edges to exact values to avoid floating-point drift.
    if y == n - 1:
        north = _WEBMERCATOR_MAX_LAT
    if y == 0:
        south = -_WEBMERCATOR_MAX_LAT
    if x == n - 1:
        east = 180.0

    return (float(west), float(south), float(east), float(north))
```