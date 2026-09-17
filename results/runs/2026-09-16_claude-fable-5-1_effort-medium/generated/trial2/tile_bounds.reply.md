```python
"""Web Mercator tile bounds for the TMS tiling scheme.

TMS addresses rows from the south (row 0 touches the southern edge of the
Web Mercator extent), unlike the XYZ/Slippy scheme which counts from the
north. The returned extent is in WGS84 degrees.
"""

import math


def _row_edge_lat(z, row_edge):
    """Latitude in degrees of a horizontal TMS tile edge.

    ``row_edge`` is a tile-row boundary index in [0, 2**z], counted from
    the south. Edge 0 is the southern limit of the Web Mercator square,
    edge 2**z is the northern limit.
    """
    n = 2 ** z
    # Fraction of the way from south (-1) to north (+1) across the square.
    t = 2.0 * row_edge / n - 1.0
    return math.degrees(math.atan(math.sinh(math.pi * t)))


def tile_bounds(z, x, y):
    """Return (west, south, east, north) in WGS84 degrees for TMS tile z/x/y.

    Parameters
    ----------
    z : int
        Zoom level (>= 0).
    x : int
        Tile column, counted from the west, in [0, 2**z).
    y : int
        Tile row, counted from the south (TMS convention), in [0, 2**z).

    Returns
    -------
    tuple of float
        (west, south, east, north) bounds in degrees.
    """
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError("zoom level must be non-negative")
    n = 2 ** z
    if not 0 <= x < n:
        raise ValueError(f"tile column {x} out of range for zoom {z}")
    if not 0 <= y < n:
        raise ValueError(f"tile row {y} out of range for zoom {z}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    south = _row_edge_lat(z, y)
    north = _row_edge_lat(z, y + 1)

    return (float(west), float(south), float(east), float(north))
```