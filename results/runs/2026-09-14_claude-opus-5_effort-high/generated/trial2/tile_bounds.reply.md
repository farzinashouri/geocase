```python
"""Web Mercator (EPSG:3857) tile bounds for the TMS tiling scheme.

TMS addresses tiles with the row origin at the *bottom* of the map, so row 0 is
the southernmost row at every zoom level.  (The XYZ/"Google" scheme used by most
slippy-map clients puts row 0 at the top; the two differ by y -> 2**z - 1 - y.)
"""

from __future__ import annotations

import math

__all__ = ["tile_bounds"]


def _mercator_latitude(row: float, n: int) -> float:
    """Latitude in degrees of the horizontal line at XYZ row index `row`.

    `row` runs from 0 at the top of the map to `n` at the bottom, where
    ``n = 2 ** z`` is the number of tiles per side.
    """
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * row / n))))


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return the WGS84 extent of a TMS tile as ``(west, south, east, north)``.

    Parameters
    ----------
    z:
        Zoom level (0 or greater).
    x:
        Tile column, counted from the west, in ``[0, 2**z)``.
    y:
        Tile row, counted from the **south** (TMS convention), in ``[0, 2**z)``.

    Returns
    -------
    A 4-tuple of floats in degrees: western longitude, southern latitude,
    eastern longitude, northern latitude.  Latitudes are clipped by the Web
    Mercator projection itself to roughly +/- 85.0511 degrees.
    """
    z = int(z)
    x = int(x)
    y = int(y)

    if z < 0:
        raise ValueError(f"zoom must be non-negative, got {z}")

    n = 1 << z
    if not 0 <= x < n:
        raise ValueError(f"x must be in [0, {n}) at zoom {z}, got {x}")
    if not 0 <= y < n:
        raise ValueError(f"y must be in [0, {n}) at zoom {z}, got {y}")

    # Flip the TMS row (origin bottom) into an XYZ row (origin top).
    top_row = n - 1 - y

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = _mercator_latitude(top_row, n)
    south = _mercator_latitude(top_row + 1, n)

    return (float(west), float(south), float(east), float(north))
```