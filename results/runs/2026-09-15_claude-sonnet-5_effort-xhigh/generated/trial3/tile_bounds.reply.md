```python
"""Tile bounds computation for Web Mercator tiles using the TMS scheme."""

import math


def tile_bounds(z, x, y):
    """Return (west, south, east, north) WGS84 degree bounds of TMS tile (z, x, y)."""
    n = 2 ** z

    def lon_deg(x_tile):
        return x_tile / n * 360.0 - 180.0

    def lat_deg(y_xyz):
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y_xyz / n)))
        return math.degrees(lat_rad)

    # TMS row y counts from the south; convert to the XYZ (top-origin) row
    # used by the standard slippy-map tile math before looking up latitudes.
    y_xyz = n - 1 - y

    west = lon_deg(x)
    east = lon_deg(x + 1)
    north = lat_deg(y_xyz)
    south = lat_deg(y_xyz + 1)

    return (float(west), float(south), float(east), float(north))
```