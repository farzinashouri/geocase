```python
"""Web Mercator TMS tile bounds computation."""

import math


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return (west, south, east, north) WGS84 degree bounds for a TMS tile.

    Parameters
    ----------
    z : int
        Zoom level.
    x : int
        Tile column.
    y : int
        Tile row, using the TMS convention (row 0 is the southernmost row).

    Returns
    -------
    tuple[float, float, float, float]
        (west, south, east, north) in WGS84 degrees.
    """
    n = 2 ** z
    # TMS numbers rows from the south; convert to the XYZ (top-down) row
    # index used by the standard Web Mercator tile-to-degrees formula.
    y_xyz = n - 1 - y

    def _lat(row: float) -> float:
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * row / n))))

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = _lat(y_xyz)
    south = _lat(y_xyz + 1)

    return (float(west), float(south), float(east), float(north))
```