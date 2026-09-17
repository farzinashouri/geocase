```python
"""Geographic bounds of Web Mercator (EPSG:3857) tiles addressed in the TMS scheme.

In the TMS scheme, tile row ``y`` counts upward from the south (bottom) edge
of the world, i.e. row 0 at zoom ``z`` touches the southern Web Mercator
limit (~-85.0511 deg). This is the vertical flip of the XYZ / "Google" scheme,
where row 0 is at the north edge.
"""

import math

__all__ = ["tile_bounds"]

_MAX_LAT = math.degrees(math.atan(math.sinh(math.pi)))  # ~85.0511287798


def _tms_row_edge_lat(z: int, row_edge: int) -> float:
    """Latitude (deg) of a horizontal tile edge, counting edges from the south."""
    n = 2 ** z
    if row_edge <= 0:
        return -_MAX_LAT
    if row_edge >= n:
        return _MAX_LAT
    # Mercator y in [-pi, pi], increasing northward.
    merc_y = math.pi * (2.0 * row_edge / n - 1.0)
    return math.degrees(math.atan(math.sinh(merc_y)))


def tile_bounds(z: int, x: int, y: int) -> tuple:
    """Return ``(west, south, east, north)`` in WGS84 degrees for TMS tile z/x/y.

    Parameters
    ----------
    z : int
        Zoom level (>= 0).
    x : int
        Tile column, 0 <= x < 2**z, increasing eastward.
    y : int
        Tile row in TMS convention, 0 <= y < 2**z, increasing northward
        (row 0 is the southernmost row).

    Returns
    -------
    tuple of float
        ``(west, south, east, north)`` longitude/latitude bounds in degrees.
    """
    z = int(z)
    x = int(x)
    y = int(y)
    if z < 0:
        raise ValueError(f"zoom must be >= 0, got {z}")
    n = 2 ** z
    if not (0 <= x < n):
        raise ValueError(f"x must be in [0, {n}) at zoom {z}, got {x}")
    if not (0 <= y < n):
        raise ValueError(f"y must be in [0, {n}) at zoom {z}, got {y}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    if x + 1 == n:
        east = 180.0

    south = _tms_row_edge_lat(z, y)
    north = _tms_row_edge_lat(z, y + 1)

    return (float(west), float(south), float(east), float(north))
```