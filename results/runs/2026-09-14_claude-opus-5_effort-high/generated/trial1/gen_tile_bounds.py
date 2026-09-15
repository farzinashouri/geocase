"""Geographic extent of Web Mercator tiles addressed with the TMS scheme.

TMS (Tile Map Service) numbers rows from the *bottom* of the map upward, so
row ``y`` covers the horizontal strip between fractions ``y / 2**z`` and
``(y + 1) / 2**z`` of the map height, measured from the south edge. This is
the vertical flip of the more common XYZ/"slippy map" convention.

The map is the standard EPSG:3857 square, which spans the full 360 degrees of
longitude and latitudes of roughly +/- 85.0511 degrees.
"""

from __future__ import annotations

import math

__all__ = ["tile_bounds"]


def _lat_from_fraction(fraction: float) -> float:
    """Latitude in degrees at ``fraction`` of the map height above its south edge."""
    # Inverse Mercator: y_merc runs from -pi (south edge) to +pi (north edge).
    y_merc = math.pi * (2.0 * fraction - 1.0)
    return math.degrees(math.atan(math.sinh(y_merc)))


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return ``(west, south, east, north)`` in WGS84 degrees for a TMS tile.

    Args:
        z: Zoom level (non-negative). The map is ``2**z`` tiles on a side.
        x: Tile column, counted eastward from the antimeridian, ``0 <= x < 2**z``.
        y: Tile row, counted *northward* from the south edge, ``0 <= y < 2**z``
           (TMS convention).

    Returns:
        A 4-tuple of floats: the western, southern, eastern and northern edges
        of the tile, in degrees of longitude/latitude.

    Raises:
        ValueError: If the zoom is negative or the tile indices fall outside
            the grid for that zoom.
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

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    # TMS rows increase northward, so y is the south edge and y + 1 the north.
    south = _lat_from_fraction(y / n)
    north = _lat_from_fraction((y + 1) / n)

    return (west, south, east, north)