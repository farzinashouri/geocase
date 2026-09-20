```python
"""Geographic bounds of Web Mercator (EPSG:3857) tiles addressed in the TMS scheme.

The TMS (Tile Map Service) scheme differs from the XYZ / "slippy map" scheme
only in the direction of the row axis: TMS row 0 is the *southernmost* row,
whereas XYZ row 0 is the northernmost.  The two are related by

    y_xyz = 2**z - 1 - y_tms

Columns run west to east in both schemes.  Importing this module has no side
effects; only the standard library is used.
"""

from __future__ import annotations

import math
import operator

__all__ = ["tile_bounds", "MAX_LATITUDE"]

#: Latitude limit of the Web Mercator projection, in degrees (~85.0511287798066).
MAX_LATITUDE: float = math.degrees(math.atan(math.sinh(math.pi)))


def _as_int(value, name: str) -> int:
    """Return ``value`` as an ``int``, rejecting non-integral input.

    Accepts real ``int`` objects and anything implementing ``__index__``
    (e.g. NumPy integer scalars), plus floats that are exactly integral
    such as ``3.0``.  Rejects ``1.5``, ``nan``, ``inf`` and non-numeric input.
    """
    try:
        return operator.index(value)
    except TypeError:
        pass
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        raise TypeError(f"{name} must be an integer, got {value!r}") from None
    if not as_float.is_integer():  # also False for nan and +/-inf
        raise ValueError(f"{name} must be an integer, got {value!r}")
    return int(as_float)


def _row_edge_latitude(row_edge: int, n: int) -> float:
    """Latitude (degrees) of the horizontal grid line ``row_edge`` rows up from the south.

    ``row_edge`` ranges from 0 (southern limit of the projection, -MAX_LATITUDE)
    to ``n`` (northern limit, +MAX_LATITUDE), where ``n`` is the number of
    rows at the zoom level.  The projected square spans Mercator y in
    ``[-pi, pi]`` (unit sphere), and latitude is the inverse Mercator
    ``atan(sinh(y))``.
    """
    mercator_y = math.pi * (2.0 * row_edge / n - 1.0)
    return math.degrees(math.atan(math.sinh(mercator_y)))


def tile_bounds(z, x, y) -> tuple[float, float, float, float]:
    """Return the WGS84 extent ``(west, south, east, north)`` of a TMS Web Mercator tile.

    Parameters
    ----------
    z : int
        Zoom level, ``>= 0``.  There are ``2**z`` columns and rows.
    x : int
        Column index, ``0 <= x < 2**z``, increasing eastward from -180 deg.
    y : int
        TMS row index, ``0 <= y < 2**z``, increasing *northward* from the
        southern limit of the projection (row 0 touches ~-85.05 deg).

    Returns
    -------
    tuple of four floats
        ``(west, south, east, north)`` in decimal degrees.

    Raises
    ------
    TypeError
        If an argument is not numeric.
    ValueError
        If an argument is not integral, ``z`` is negative, or ``x``/``y``
        fall outside the grid for zoom ``z``.

    Examples
    --------
    >>> tile_bounds(0, 0, 0)
    (-180.0, -85.0511287798066, 180.0, 85.0511287798066)
    >>> tile_bounds(1, 0, 0)   # south-west quadrant (TMS row 0 is the south)
    (-180.0, -85.0511287798066, 0.0, 0.0)
    >>> tile_bounds(1, 1, 1)   # north-east quadrant
    (0.0, 0.0, 180.0, 85.0511287798066)
    """
    z = _as_int(z, "z")
    x = _as_int(x, "x")
    y = _as_int(y, "y")

    if z < 0:
        raise ValueError(f"z must be non-negative, got {z}")
    n = 1 << z  # tiles per axis at this zoom
    if not 0 <= x < n:
        raise ValueError(f"x must satisfy 0 <= x < {n} at zoom {z}, got {x}")
    if not 0 <= y < n:
        raise ValueError(f"y must satisfy 0 <= y < {n} at zoom {z}, got {y}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    south = _row_edge_latitude(y, n)
    north = _row_edge_latitude(y + 1, n)

    return (float(west), float(south), float(east), float(north))
```