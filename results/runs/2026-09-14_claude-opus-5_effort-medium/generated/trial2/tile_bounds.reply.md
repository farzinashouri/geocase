```python
"""Geographic bounds of Web Mercator tiles addressed in the TMS scheme.

TMS (Tile Map Service) numbers rows from the *bottom* of the map upward, so
row 0 is the southernmost row at every zoom level.  This differs from the
"slippy map" / XYZ convention, where row 0 is the northernmost.
"""

from __future__ import annotations

import math

__all__ = ["tile_bounds"]


def _latitude(fraction: float) -> float:
    """Latitude in degrees at `fraction` of the map height, measured from the
    bottom edge (0.0 = south edge, 1.0 = north edge) of the Web Mercator plane.
    """
    return math.degrees(math.atan(math.sinh(math.pi * (2.0 * fraction - 1.0))))


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return the WGS84 extent of a TMS tile as (west, south, east, north).

    Parameters
    ----------
    z : int
        Zoom level (>= 0).
    x : int
        Tile column, increasing eastward, in [0, 2**z - 1].
    y : int
        Tile row, increasing *northward* (TMS convention), in [0, 2**z - 1].

    Returns
    -------
    tuple of four floats
        (west, south, east, north) in degrees.  Longitudes span [-180, 180];
        latitudes are clamped by the Web Mercator limit of ~+/-85.0511.
    """
    z = int(z)
    x = int(x)
    y = int(y)

    if z < 0:
        raise ValueError(f"zoom must be non-negative, got {z}")

    n = 1 << z
    if not (0 <= x < n):
        raise ValueError(f"x must be in [0, {n - 1}] at zoom {z}, got {x}")
    if not (0 <= y < n):
        raise ValueError(f"y must be in [0, {n - 1}] at zoom {z}, got {y}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    # TMS rows count up from the south edge, so y/n is already the fraction
    # of map height at the tile's southern edge.
    south = _latitude(y / n)
    north = _latitude((y + 1) / n)

    return (float(west), float(south), float(east), float(north))
```