```python
"""Web Mercator tile bounds for the TMS tiling scheme.

TMS (Tile Map Service) addresses tiles with the row origin at the *bottom*
(south) of the map, unlike the XYZ/"slippy map" scheme where row 0 is the top.
"""

from __future__ import annotations

import math

__all__ = ["tile_bounds"]


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return the WGS84 extent of a TMS Web Mercator tile.

    Parameters
    ----------
    z:
        Zoom level (``z >= 0``). The map is ``2**z`` tiles on a side.
    x:
        Tile column, increasing eastward, in ``[0, 2**z - 1]``.
    y:
        Tile row, increasing *northward* (TMS convention), in ``[0, 2**z - 1]``.

    Returns
    -------
    tuple of float
        ``(west, south, east, north)`` in degrees of longitude/latitude.
        Latitudes are clamped to the Web Mercator limits of
        ``+/-85.0511287798...`` degrees at the extreme rows.
    """
    z = _as_index(z, "z")
    x = _as_index(x, "x")
    y = _as_index(y, "y")

    n_tiles = 1 << z
    if not 0 <= x < n_tiles:
        raise ValueError(f"x must be in [0, {n_tiles - 1}] at zoom {z}, got {x}")
    if not 0 <= y < n_tiles:
        raise ValueError(f"y must be in [0, {n_tiles - 1}] at zoom {z}, got {y}")

    west = x / n_tiles * 360.0 - 180.0
    east = (x + 1) / n_tiles * 360.0 - 180.0

    # TMS rows count up from the south; convert to XYZ rows (counting down from
    # the north) so the usual Mercator inverse applies.
    y_xyz = n_tiles - 1 - y
    north = _lat(y_xyz, n_tiles)
    south = _lat(y_xyz + 1, n_tiles)

    return (float(west), float(south), float(east), float(north))


def _lat(row: int, n_tiles: int) -> float:
    """Latitude in degrees of an XYZ row edge (``row`` counted from the north)."""
    t = math.pi * (1.0 - 2.0 * row / n_tiles)
    return math.degrees(math.atan(math.sinh(t)))


def _as_index(value: object, name: str) -> int:
    """Coerce a tile index to ``int``, rejecting bools and non-integral input."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if name == "z" and value < 0:
        raise ValueError(f"z must be non-negative, got {value}")
    return value
```