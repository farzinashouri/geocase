```python
"""Geographic extent of Web Mercator map tiles addressed with the TMS scheme.

Web Mercator (EPSG:3857) tiles subdivide the square projected world into a
``2**z x 2**z`` grid at zoom level ``z``.  Two conventions exist for numbering
the rows of that grid:

* **TMS** (OSGeo Tile Map Service, used here): row ``y`` is counted from the
  *bottom* (south) of the world, so ``y = 0`` is the southernmost row.
* **XYZ** / "slippy map" (OpenStreetMap, Google, most web clients): row ``y``
  is counted from the *top* (north), so ``y = 0`` is the northernmost row.

The two are related by ``y_tms = 2**z - 1 - y_xyz``; pass a slippy-map row
through that expression before calling :func:`tile_bounds`.

Importing this module has no side effects.
"""

from __future__ import annotations

import math
import operator

__all__ = ["tile_bounds", "MAX_LATITUDE"]

#: Latitude (degrees) of the north edge of the Web Mercator world square; the
#: south edge is its negation.  The projection is undefined at the poles, so
#: tiles never reach beyond +/- this value.
MAX_LATITUDE: float = math.degrees(math.atan(math.sinh(math.pi)))


def _latitude(fraction: float) -> float:
    """Convert a fraction of the world square, measured from its south edge, to degrees.

    This is the inverse Mercator projection: ``fraction`` 0.0 maps to
    ``-MAX_LATITUDE``, 0.5 to the equator, and 1.0 to ``+MAX_LATITUDE``.
    """
    return math.degrees(math.atan(math.sinh(math.pi * (2.0 * fraction - 1.0))))


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return the WGS84 extent of a TMS Web Mercator tile.

    Args:
        z: Zoom level; the world is divided into ``2**z`` columns and rows.
        x: Tile column, counted eastward from the antimeridian, ``0 <= x < 2**z``.
        y: Tile row, counted **northward from the south edge** (TMS
            convention), ``0 <= y < 2**z``.

    Returns:
        ``(west, south, east, north)`` as four floats in degrees of longitude
        and latitude (EPSG:4326).

    Raises:
        TypeError: If any argument is not an integer.
        ValueError: If ``z`` is negative or ``x`` or ``y`` falls outside the
            grid for that zoom level.

    >>> tile_bounds(0, 0, 0)  # doctest: +ELLIPSIS
    (-180.0, -85.05112877980659, 180.0, 85.05112877980659)
    >>> tile_bounds(1, 0, 0)  # south-west quadrant, since TMS rows start south
    (-180.0, -85.05112877980659, 0.0, 0.0)
    """
    z = operator.index(z)
    x = operator.index(x)
    y = operator.index(y)

    if z < 0:
        raise ValueError(f"zoom must be non-negative, got {z}")

    n = 1 << z  # tiles per axis at this zoom
    if not 0 <= x < n:
        raise ValueError(f"column x must satisfy 0 <= x < {n} at zoom {z}, got {x}")
    if not 0 <= y < n:
        raise ValueError(f"row y must satisfy 0 <= y < {n} at zoom {z}, got {y}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    south = _latitude(y / n)
    north = _latitude((y + 1) / n)

    return (west, south, east, north)
```