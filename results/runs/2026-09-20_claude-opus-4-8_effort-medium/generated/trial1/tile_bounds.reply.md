```python
"""Compute the WGS84 geographic bounds of a TMS Web Mercator tile."""

import math


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for a TMS tile.

    Tiles use the TMS addressing scheme, where the row index `y` increases
    northward (row 0 is the southernmost tile), as opposed to the XYZ/Google
    scheme where row 0 is the northernmost tile.
    """
    n = 2 ** z

    # Convert the TMS row (origin at the bottom/south) to the XYZ row
    # convention (origin at the top/north) used by the math below.
    y_xyz = n - 1 - y

    def _lon(xt):
        return xt / n * 360.0 - 180.0

    def _lat(yt):
        # yt measured from the top (north) edge in XYZ convention.
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yt / n))))

    west = _lon(x)
    east = _lon(x + 1)
    north = _lat(y_xyz)
    south = _lat(y_xyz + 1)

    return (float(west), float(south), float(east), float(north))
```