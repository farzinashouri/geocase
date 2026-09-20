"""Geographic bounds of Web Mercator tiles addressed with the TMS scheme.

TMS (Tile Map Service) numbers tile rows from the south: at zoom ``z`` the
row ``y = 0`` is the bottom-most tile and ``y = 2**z - 1`` the top-most one.
This is the opposite of the XYZ / "Google" convention, where row 0 is at the
north; the two differ by ``y_xyz = 2**z - 1 - y_tms``.

Tiles cover the standard Web Mercator (EPSG:3857) extent, so the world is
square and latitude is clipped to about +/-85.0511 degrees.
"""

from __future__ import annotations

import math

__all__ = ["tile_bounds"]


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Return the WGS84 extent of a TMS tile as ``(west, south, east, north)``.

    Args:
        z: Zoom level; there are ``2**z`` tile columns and rows.
        x: Tile column, counted eastward from the antimeridian (``0``-based).
        y: Tile row, counted **northward from the south** (TMS convention).

    Returns:
        A 4-tuple of floats in degrees: western longitude, southern latitude,
        eastern longitude, northern latitude.

    Raises:
        ValueError: If ``z`` is negative or ``x``/``y`` fall outside the
            ``[0, 2**z - 1]`` range valid for that zoom level.

    Examples:
        >>> tile_bounds(0, 0, 0)  # doctest: +ELLIPSIS
        (-180.0, -85.05112877980659, 180.0, 85.05112877980659)
        >>> tile_bounds(1, 0, 0)  # south-west quadrant in TMS
        (-180.0, -85.05112877980659, 0.0, 0.0)
    """
    if z < 0:
        raise ValueError(f"zoom must be non-negative, got {z!r}")

    n = 1 << z  # number of tiles per axis; also rejects non-integer zooms
    if not 0 <= x < n:
        raise ValueError(f"x must be in [0, {n - 1}] at zoom {z}, got {x!r}")
    if not 0 <= y < n:
        raise ValueError(f"y must be in [0, {n - 1}] at zoom {z}, got {y!r}")

    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    # In TMS the row index grows northward, so y is the tile's southern edge.
    south = _latitude(y / n)
    north = _latitude((y + 1) / n)
    return (west, south, east, north)


def _latitude(v: float) -> float:
    """Latitude in degrees of the Mercator line at fraction ``v`` from the south.

    ``v`` runs from 0.0 at the bottom of the Web Mercator square to 1.0 at the
    top, i.e. the inverse of the spherical Mercator projection.
    """
    return math.degrees(math.atan(math.sinh(math.pi * (2.0 * v - 1.0))))