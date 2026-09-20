"""Geographic bounds of Web Mercator tiles addressed with the TMS scheme.

The TMS (Tile Map Service) scheme splits the Web Mercator (EPSG:3857) plane
into ``2**z`` columns and ``2**z`` rows at zoom level ``z``.  Column ``x``
increases eastward from the antimeridian and row ``y`` increases *northward*
from the southern edge of the projected extent -- the opposite of the XYZ /
"slippy map" convention, where row 0 is the northernmost row.
"""

from __future__ import annotations

import math

__all__ = ["tile_bounds"]

# Latitude at which the Web Mercator projection is truncated to keep the map
# square: atan(sinh(pi)) in degrees.
MAX_LATITUDE = math.degrees(math.atan(math.sinh(math.pi)))


def _latitude(y_fraction: float) -> float:
    """Return the WGS84 latitude of a horizontal line in the Mercator plane.

    ``y_fraction`` is the position of the line measured from the southern edge
    of the projected extent, in the range [0.0, 1.0].
    """
    return math.degrees(math.atan(math.sinh(math.pi * (2.0 * y_fraction - 1.0))))


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return ``(west, south, east, north)`` of a TMS tile, in WGS84 degrees.

    Parameters
    ----------
    z:
        Zoom level; must be a non-negative integer.
    x:
        Tile column, increasing eastward, in ``[0, 2**z - 1]``.
    y:
        Tile row, increasing *northward* (TMS convention), in
        ``[0, 2**z - 1]``.

    Returns
    -------
    tuple of float
        The tile's extent as ``(west, south, east, north)``.  Longitudes lie in
        [-180, 180] and latitudes in [-85.0511..., 85.0511...], the limits of
        the Web Mercator projection.

    Raises
    ------
    ValueError
        If ``z`` is negative, or if ``x`` or ``y`` falls outside the valid
        range for the given zoom level.
    TypeError
        If any argument is not an integer.

    Examples
    --------
    >>> tile_bounds(0, 0, 0)  # doctest: +ELLIPSIS
    (-180.0, -85.0511..., 180.0, 85.0511...)
    >>> west, south, east, north = tile_bounds(1, 0, 0)
    >>> (west, east, round(north, 6))
    (-180.0, 0.0, 0.0)
    """
    for name, value in (("z", z), ("x", x), ("y", y)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an int, got {type(value).__name__}")

    if z < 0:
        raise ValueError(f"z must be non-negative, got {z}")

    n = 1 << z  # number of tiles per axis at this zoom level
    if not 0 <= x < n:
        raise ValueError(f"x must be in [0, {n - 1}] at zoom {z}, got {x}")
    if not 0 <= y < n:
        raise ValueError(f"y must be in [0, {n - 1}] at zoom {z}, got {y}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    # TMS rows count northward from the bottom, so y is the southern edge.
    south = -MAX_LATITUDE if y == 0 else _latitude(y / n)
    north = MAX_LATITUDE if y + 1 == n else _latitude((y + 1) / n)

    return (west, south, east, north)